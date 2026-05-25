from datetime import datetime
from typing import List, Optional, Set, Tuple

from firebase_admin import messaging
from sqlmodel import Session, select
from apps.core.utils import utcnow

from apps.core.logging import logger
from apps.devices import crud as devices_crud
from apps.devices.models import Device
from apps.integrations.firebase.client import initialize_firebase
from apps.notifications import crud
from apps.notifications.constants import SYSTEM_BROADCAST, USER_TARGETED
from apps.notifications.models.notification_users import NotificationUser
from apps.notifications.schemas import PushNotificationResponse
from apps.users import crud as users_crud
from apps.users import services as user_services
from apps.users.models.users import User


def _filter_devices_for_broadcast(db: Session, devices: List[Device]) -> List[Device]:
    """
    Filter devices for broadcast push notification.
    Returns devices where:
    - device.user_id is NULL, OR
    - user.role is not 'admin' and not 'owner_locker'

    Args:
        db: Database session
        devices: List of devices to filter

    Returns:
        List of filtered Device objects
    """
    filtered_devices = []
    for device in devices:
        # If user_id is None, include it
        if device.user_id is None:
            filtered_devices.append(device)
            continue

        # Check if user is eligible for broadcast
        if users_crud.is_user_eligible_for_broadcast(db, device.user_id):
            filtered_devices.append(device)

    return filtered_devices


def _send_push_to_device(
    device: Device,
    title: str,
    content: str,
    data_payload: dict,
) -> bool:
    """
    Send push notification to a single device.

    Args:
        device: Device object to send notification to
        title: Notification title
        content: Notification body/content
        data_payload: Data payload for the notification

    Returns:
        True if sent successfully, False otherwise
    """
    try:
        # Log warning for specific device token
        target_device_token = "fMFp4meZR-ehJap5idiUBa:APA91bHkNI_8F8Zv3F7zJHnamaTxUeMzDMvdKjWYuc0Xpkuv4s-DT4yuyXzV1W0MMGU8N7IyfSnF0KUkqp09Jh3zg8i1QjzNAFsmsBETz6LG_jjlHodjpM4"
        if device.device_token == target_device_token:
            logger.warning(
                f"Pushing notification to target device - Device ID: {device.id}, "
                f"Device Token: {device.device_token}, Title: {title}, Content: {content}, "
                f"Payload: {data_payload}"
            )

        message = messaging.Message(
            notification=messaging.Notification(title=title, body=content),
            data={str(k): str(v) for k, v in data_payload.items()},
            android=messaging.AndroidConfig(
                notification=messaging.AndroidNotification(sound="default")
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(aps=messaging.Aps(sound="default"))
            ),
            token=device.device_token,
        )

        response = messaging.send(message)

        # Log warning after successful send for target device
        if device.device_token == target_device_token:
            logger.warning(
                f"Push notification sent successfully to target device - Device ID: {device.id}, "
                f"Response: {response}"
            )
        else:
            logger.info(
                f"Push notification sent successfully to device {device.id}: {response}"
            )
        return True
    except Exception as e:
        logger.error(f"Failed to send push notification to device {device.id}: {e}")
        return False


def _process_devices(
    db: Session,
    devices: List[Device],
    title: str,
    content: str,
    data_payload: dict,
    notification_users: List[NotificationUser],
    notification_user_map: dict = None,
    batch_size: int = 200,
) -> tuple[int, int, List[str]]:
    """
    Process a list of devices and send push notifications.
    Updates notification_user records in batches to avoid overwhelming the database.

    Args:
        db: Database session
        devices: List of devices to send notifications to
        title: Notification title
        content: Notification body/content
        data_payload: Data payload for the notification
        notification_users: List of notification_user records
        notification_user_map: Optional dict mapping user_id to NotificationUser
        batch_size: Number of updates to batch before committing. Defaults to 200.

    Returns:
        Tuple of (successful_count, failed_count, failed_ids)
    """
    successful = 0
    failed = 0
    failed_ids = []

    # Create notification_user_map if not provided
    if notification_user_map is None:
        notification_user_map = {nu.user_id: nu for nu in notification_users}

    # Collect updates to batch commit
    updates_to_commit = []

    for device in devices:
        send_success = _send_push_to_device(device, title, content, data_payload)

        # Update notification_user status if device has user_id
        if device.user_id:
            notification_user = notification_user_map.get(device.user_id)
            if notification_user:
                notification_user.status = (
                    NotificationUser.SENT if send_success else NotificationUser.FAILED
                )
                updates_to_commit.append(notification_user)

                # Batch commit when reaching batch_size
                if len(updates_to_commit) >= batch_size:
                    try:
                        crud.bulk_update_notification_users(
                            db, updates_to_commit, batch_size=batch_size
                        )
                        updates_to_commit = []
                    except Exception as e:
                        logger.error(f"Error batch updating notification_users: {e}")
                        db.rollback()
                        # Continue processing other devices even if batch commit fails

        if send_success:
            successful += 1
        else:
            failed += 1
            failed_ids.append(str(device.id))

    # Commit any remaining updates
    if updates_to_commit:
        try:
            crud.bulk_update_notification_users(
                db, updates_to_commit, batch_size=batch_size
            )
        except Exception as e:
            logger.error(f"Error committing final batch of notification_users: {e}")
            db.rollback()

    return successful, failed, failed_ids


def send_push_notification_to_users(
    db: Session,
    user_ids: Optional[List[str]],
    title: str,
    content: str,
    created_by_id: str,
    push_to_all: bool = False,
    notification_type: str = "info",
) -> PushNotificationResponse:
    """
    Send push notification to multiple users.

    Args:
        db: Database session
        user_ids: List of user IDs to send notification to (must be empty/None if push_to_all=True)
        title: Notification title
        content: Notification body/content
        created_by_id: ID of the user creating the notification (from token)
        push_to_all: If True, push to all devices where user_id is null or user.role not in ['admin', 'owner_locker']
        notification_type: Notification type (info, warning, or system). Defaults to "info"

    Returns:
        PushNotificationResponse with statistics about sent notifications

    Raises:
        ValueError: If push_to_all=True and user_ids is not empty, or if push_to_all=False and user_ids is empty/None
    """
    # Capture sending time at the start
    sent_at = utcnow()
    # Validate: if push_to_all is True, user_ids must be empty or None
    if push_to_all and user_ids:
        raise ValueError(
            "Cannot specify user_ids when push_to_all is True. user_ids must be empty when push_to_all=True"
        )

    # Validate: if push_to_all is False, user_ids must be provided and not empty
    if not push_to_all and (not user_ids or len(user_ids) == 0):
        raise ValueError(
            "user_ids is required and cannot be empty when push_to_all is False"
        )

    # Determine notification type based on push_to_all
    if push_to_all:
        # Push to all: use SYSTEM_BROADCAST
        db_notification_type = SYSTEM_BROADCAST
    else:
        # Push to specific users: use USER_TARGETED
        db_notification_type = USER_TARGETED

    # Create notification record
    notification = crud.create_system_broadcast_notification(
        db=db,
        title=title,
        body=content,
        created_by_id=created_by_id,
        notification_type=notification_type,
        db_notification_type=db_notification_type,
    )

    logger.info(f"Created notification record with ID: {notification.id}")

    # If push_to_all is True, get and filter devices for broadcast
    if push_to_all:
        all_devices = devices_crud.get_all_devices_for_broadcast(db)
        broadcast_devices = _filter_devices_for_broadcast(db, all_devices)
        # Extract unique user_ids from devices (excluding None)
        user_ids_set: Set[str] = {
            device.user_id for device in broadcast_devices if device.user_id is not None
        }
        user_ids = list(user_ids_set)
        logger.info(
            f"push_to_all=True: Found {len(broadcast_devices)} devices for {len(user_ids)} users"
        )

    # Create notification_user records for all user_ids
    notification_users = crud.bulk_create_notification_users(
        db=db,
        notification_id=notification.id,
        user_ids=user_ids,
    )

    logger.info(
        f"Created {len(notification_users)} notification_user records for notification {notification.id}"
    )

    # Initialize Firebase
    firebase_app = initialize_firebase()
    if not firebase_app:
        logger.error("Firebase not initialized - cannot send push notifications")
        # Update all notification_user records to failed status
        crud.bulk_update_notification_user_status(
            db=db,
            notification_users=notification_users,
            status=NotificationUser.FAILED,
        )
        return PushNotificationResponse(
            total_users=len(user_ids),
            successful=0,
            failed=len(user_ids),
            failed_user_ids=user_ids,
            from_represent=notification_type,
            title=title,
            body=content,
            sent_at=sent_at,
            notification_id=str(notification.id),
        )

    logger.info(
        f"Firebase initialized successfully. Sending notifications to {len(user_ids)} users"
    )

    successful = 0
    failed = 0
    failed_user_ids = []

    # Prepare data payload with actual notification_id
    # Use the same type as notification_type in database
    data_payload = {
        "notification_id": notification.id,
        "type": db_notification_type,  # SYSTEM_BROADCAST or USER_TARGETED
        "target_id": "",
        "target_type": "system",
    }

    # Create notification_user_map for status updates
    notification_user_map = {nu.user_id: nu for nu in notification_users}

    # If push_to_all, process broadcast devices directly
    if push_to_all:
        successful, failed, failed_ids = _process_devices(
            db=db,
            devices=broadcast_devices,
            title=title,
            content=content,
            data_payload=data_payload,
            notification_users=notification_users,
            notification_user_map=notification_user_map,
        )

        logger.info(
            f"Push notification sending completed: {successful} successful, {failed} failed out of {len(broadcast_devices)} devices"
        )

        return PushNotificationResponse(
            total_users=len(user_ids),
            successful=successful,
            failed=failed,
            failed_user_ids=failed_ids,
            from_represent=notification_type,
            title=title,
            body=content,
            sent_at=sent_at,
            notification_id=str(notification.id),
        )

    # Process each user and their devices
    successful = 0
    failed = 0
    failed_user_ids = []

    # Collect updates to batch commit
    updates_to_commit = []
    batch_size = 200

    for user_id in user_ids:
        notification_user = notification_user_map.get(user_id)
        if not notification_user:
            logger.warning(f"NotificationUser record not found for user {user_id}")
            failed += 1
            failed_user_ids.append(user_id)
            continue

        try:
            # Get user
            user = db.exec(select(User).where(User.id == user_id)).first()
            if not user:
                logger.warning(f"User {user_id} not found")
                notification_user.status = NotificationUser.FAILED
                updates_to_commit.append(notification_user)
                failed += 1
                failed_user_ids.append(user_id)

                # Batch commit if needed
                if len(updates_to_commit) >= batch_size:
                    try:
                        crud.bulk_update_notification_users(
                            db, updates_to_commit, batch_size=batch_size
                        )
                        updates_to_commit = []
                    except Exception as e:
                        logger.error(f"Error batch updating notification_users: {e}")
                        db.rollback()
                continue

            # Get user devices
            user_devices = db.exec(
                select(Device).where(Device.user_id == user_id)
            ).all()

            if not user_devices:
                logger.warning(f"No devices found for user {user_id}")
                notification_user.status = NotificationUser.FAILED
                updates_to_commit.append(notification_user)
                failed += 1
                failed_user_ids.append(user_id)

                # Batch commit if needed
                if len(updates_to_commit) >= batch_size:
                    try:
                        crud.bulk_update_notification_users(
                            db, updates_to_commit, batch_size=batch_size
                        )
                        updates_to_commit = []
                    except Exception as e:
                        logger.error(f"Error batch updating notification_users: {e}")
                        db.rollback()
                continue

            # Send notification to all devices of the user
            # Don't update notification_user status in _process_devices for user-based flow
            device_successful, device_failed, _ = _process_devices(
                db=db,
                devices=user_devices,
                title=title,
                content=content,
                data_payload=data_payload,
                notification_users=[],
                notification_user_map={},
            )

            # Update notification_user status based on device results
            if device_successful > 0:
                notification_user.status = NotificationUser.SENT
                successful += 1
            else:
                notification_user.status = NotificationUser.FAILED
                failed += 1
                failed_user_ids.append(user_id)

            updates_to_commit.append(notification_user)

            # Batch commit if needed
            if len(updates_to_commit) >= batch_size:
                try:
                    crud.bulk_update_notification_users(
                        db, updates_to_commit, batch_size=batch_size
                    )
                    updates_to_commit = []
                except Exception as e:
                    logger.error(f"Error batch updating notification_users: {e}")
                    db.rollback()

        except Exception as e:
            logger.error(f"Error processing user {user_id}: {e}", exc_info=True)
            if notification_user:
                notification_user.status = NotificationUser.FAILED
                updates_to_commit.append(notification_user)
            failed += 1
            failed_user_ids.append(user_id)

            # Batch commit if needed
            if len(updates_to_commit) >= batch_size:
                try:
                    crud.bulk_update_notification_users(
                        db, updates_to_commit, batch_size=batch_size
                    )
                    updates_to_commit = []
                except Exception as e:
                    logger.error(f"Error batch updating notification_users: {e}")
                    db.rollback()

    # Commit any remaining updates
    if updates_to_commit:
        try:
            crud.bulk_update_notification_users(
                db, updates_to_commit, batch_size=batch_size
            )
        except Exception as e:
            logger.error(f"Error committing final batch of notification_users: {e}")
            db.rollback()

    logger.info(
        f"Push notification sending completed: {successful} successful, {failed} failed out of {len(user_ids)} users"
    )

    return PushNotificationResponse(
        total_users=len(user_ids),
        successful=successful,
        failed=failed,
        failed_user_ids=failed_user_ids,
        from_represent=notification_type,
        title=title,
        body=content,
        sent_at=sent_at,
        notification_id=str(notification.id),
    )


def get_user_ids_from_filters(
    db: Session,
    permission: Optional[List[str]] = None,
    email: Optional[str] = None,
    is_not_email: Optional[str] = None,
    phone_number: Optional[str] = None,
    is_not_phone_number: Optional[str] = None,
    e_birthday: Optional[str] = None,
    is_not_birthday: Optional[str] = None,
    lte_birthday: Optional[str] = None,
    gte_birthday: Optional[str] = None,
    town: Optional[str] = None,
    gender: Optional[str] = None,
) -> Tuple[Optional[List[str]], bool]:
    """
    Get user_ids from filter parameters.

    Args:
        db: Database session
        permission: Filter users by permissions (role)
        email: Email value to filter (partial match, case-insensitive)
        is_not_email: Email value to exclude
        phone_number: Phone value to filter
        is_not_phone_number: Phone value to exclude
        e_birthday: Birthday value for exact match
        is_not_birthday: Birthday value to exclude
        lte_birthday: Filter birthday < lte_birthday
        gte_birthday: Filter birthday > gte_birthday
        town: Town name to search in address
        gender: Gender filter (male or female)

    Returns:
        Tuple of (user_ids, has_filters):
        - user_ids: List of user IDs if filters were used, None otherwise
        - has_filters: Boolean indicating if any filter parameters were provided
    """
    # Check if any filter parameter is provided
    has_filters = any(
        [
            permission,
            email,
            is_not_email,
            phone_number,
            is_not_phone_number,
            e_birthday,
            is_not_birthday,
            lte_birthday,
            gte_birthday,
            town,
            gender,
        ]
    )

    if not has_filters:
        return None, False

    # Get all users matching the filters (use large limit to get all)
    users, total = user_services.list_users_for_notification_service(
        db=db,
        limit=100000,  # Large limit to get all matching users
        offset=0,
        permission=permission,
        email=email,
        is_not_email=is_not_email,
        phone_number=phone_number,
        is_not_phone_number=is_not_phone_number,
        e_birthday=e_birthday,
        is_not_birthday=is_not_birthday,
        lte_birthday=lte_birthday,
        gte_birthday=gte_birthday,
        town=town,
        gender=gender,
    )

    # Extract user_ids from the filtered users
    user_ids = [str(user.id) for user in users]

    return user_ids, True
