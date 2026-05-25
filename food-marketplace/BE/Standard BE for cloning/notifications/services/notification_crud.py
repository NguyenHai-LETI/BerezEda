from datetime import timedelta
from typing import Optional

from apps.core.schemas import (
    DEFAULT_LIMIT,
    DEFAULT_OFFSET,
    ListResponse,
    SuccessResponse,
)
from apps.notifications import crud, schemas
from apps.notifications.exceptions import notification_not_found
from apps.notifications.models import Notification, NotificationUser
from apps.orders.crud import get_order_by_id
from apps.shops.crud import get_shop
from apps.users.crud import get_user
from apps.users.models import User
from apps.users.validators import validate_user_exists


def _get_shop_info(db, order):
    """Helper function to get shop information from order"""
    if not order or not order.shop_id:
        return None

    shop = get_shop(db, order.shop_id)
    if shop:
        return {
            "store_name": shop.name,
            "phone_number": shop.phone,
        }
    return None


def _get_order_info(order):
    """Helper function to get order information"""
    if not order:
        return None

    return {
        "order_id": str(order.id),
        "shop_id": str(order.shop_id),
        "pickup_code": order.pickup_code,
    }


def list_notifications_service(
    db, user: User, limit: int = DEFAULT_LIMIT, offset: int = DEFAULT_OFFSET
):
    """Return notifications only for the given user_id."""
    if user is None:
        notifications, total = crud.get_system_notifications(db, limit, offset)
    else:
        user_id = user.id
        notifications, total = crud.get_notifications_for_user(
            db, user_id, limit, offset
        )

    # Build notification data with order information if applicable
    notification_data = []
    for noti in notifications:
        shop_info = None
        order_info = None

        # If target_type is "order", get order details and shop info
        if noti.target_type == "order" and noti.target_id:
            order = get_order_by_id(db, str(noti.target_id))
            if order:
                order_info = _get_order_info(order)
                shop_info = _get_shop_info(db, order)

        # Build with shop info and order info
        notification_data.append(
            schemas.NotificationRead.build(
                noti, noti.notification_user, shop_info, order_info
            )
        )

    return ListResponse(
        limit=limit,
        offset=offset,
        total=total,
        data=notification_data,
    )


def list_admin_notifications_service(
    db,
    user: User,
    limit: int = DEFAULT_LIMIT,
    offset: int = DEFAULT_OFFSET,
    search: Optional[str] = None,
):
    """
    Return notifications based on user role:
    - If admin: return ALL notifications with created_by_role field
    - If owner_locker: return only notifications created by this user

    Args:
        db: Database session
        user: User object (admin or owner_locker)
        limit: Maximum number of records to return
        offset: Number of records to skip
        search: Optional search term to filter by title or body

    Returns:
        ListResponse with paginated notifications
    """
    # Strip search parameter and convert empty string to None
    if search is not None:
        search = search.strip()
        if not search:
            search = None

    # Check user role
    if user.role == "admin":
        # Admin sees all notifications
        notifications, total = crud.get_notifications(
            db, limit=limit, offset=offset, search=search
        )
    else:
        # Owner_locker sees only their own notifications
        notifications, total = crud.get_notifications_by_created_by_id(
            db, created_by_id=str(user.id), limit=limit, offset=offset, search=search
        )

    # Build notification data with order information and created_by_role
    notification_data = []
    for noti in notifications:
        shop_info = None
        order_info = None
        created_by_role = None

        # Get created_by_role if notification has created_by_id
        if noti.created_by_id:
            creator = get_user(db, noti.created_by_id)
            if creator:
                created_by_role = creator.role

        # If target_type is "order", get order details and shop info
        if noti.target_type == "order" and noti.target_id:
            order = get_order_by_id(db, str(noti.target_id))
            if order:
                order_info = _get_order_info(order)
                shop_info = _get_shop_info(db, order)

        # Build notification with created_by_role
        notification_obj = schemas.NotificationRead.build(
            noti, None, shop_info, order_info, created_by_role=created_by_role
        )

        # Convert UTC to JST by adding 9 hours
        if notification_obj.created_at:
            notification_obj.created_at = notification_obj.created_at + timedelta(
                hours=9
            )

        notification_data.append(notification_obj)

    return ListResponse(
        limit=limit,
        offset=offset,
        total=total,
        data=notification_data,
    )


def create_notification_service(notification: schemas.NotificationCreate, db):
    if notification.target_id:
        validate_user_exists(get_user(db, notification.target_id))
    if notification.created_by_id:
        validate_user_exists(get_user(db, notification.created_by_id))

    new_notification = Notification(**notification.model_dump())
    new_notification = crud.create_notification(db, new_notification)

    if notification.target_id:
        new_notification_user = NotificationUser(
            notification_id=new_notification.id, user_id=notification.target_id
        )
        response_data = schemas.NotificationRead.build(
            new_notification, new_notification_user
        )
        crud.create_notification_user(db, new_notification_user)
    else:
        response_data = schemas.NotificationRead.build(new_notification, None)
    return SuccessResponse(data=response_data)


def get_public_notification_service(notification_id: str, db):
    """
    Get notification by ID (public endpoint, no authentication required).

    Returns the notification record from the database without user-specific data.
    """
    notification = crud.get_notification(db, notification_id)
    if not notification:
        raise notification_not_found()

    # Get shop info and order info if target_type is "order"
    shop_info = None
    order_info = None
    if notification.target_type == "order" and notification.target_id:
        order = get_order_by_id(db, str(notification.target_id))
        if order:
            order_info = _get_order_info(order)
            shop_info = _get_shop_info(db, order)

    return SuccessResponse(
        data=schemas.NotificationRead.build(notification, None, shop_info, order_info)
    )


def get_notification_service(user: User, notification_id: str, db):
    notification = crud.get_notification(db, notification_id)
    notification_user = crud.get_notification_user(
        db=db, notification_id=notification_id, user_id=user.id
    )
    if not notification or not notification_user:
        raise notification_not_found()
    notification_user.is_read = True
    crud.update_notification_user(db, notification_user)

    # Get shop info and order info if target_type is "order"
    shop_info = None
    order_info = None
    if notification.target_type == "order" and notification.target_id:
        order = get_order_by_id(db, str(notification.target_id))
        if order:
            order_info = _get_order_info(order)
            shop_info = _get_shop_info(db, order)

    return SuccessResponse(
        data=schemas.NotificationRead.build(
            notification, notification_user, shop_info, order_info
        )
    )


def update_notification_service(
    notification_id: str, user: User, confirm_content: str, db
):
    notification = crud.get_notification(db, notification_id)
    notification_user = crud.get_notification_user(db, notification_id, user.id)

    if not notification or not notification_user:
        raise notification_not_found()

    notification_user.confirm_content = confirm_content
    notification_user.is_read = True
    crud.update_notification_user(db, notification_user)

    # Get shop info and order info if target_type is "order"
    shop_info = None
    order_info = None
    if notification.target_type == "order" and notification.target_id:
        order = get_order_by_id(db, str(notification.target_id))
        if order:
            order_info = _get_order_info(order)
            shop_info = _get_shop_info(db, order)

    return SuccessResponse(
        data=schemas.NotificationRead.build(
            notification, notification_user, shop_info, order_info
        )
    )


def confirm_notification_service(
    notification_id: str, user: User, confirm_content: str, db
):
    """
    Handle user confirmation response for a notification (e.g., product expiry reached).
    Sets is_confirmed, confirm_content, confirmed_at, and marks as read.
    """
    from datetime import datetime, timezone

    notification = crud.get_notification(db, notification_id)
    notification_user = crud.get_notification_user(db, notification_id, user.id)

    if not notification or not notification_user:
        raise notification_not_found()

    notification_user.is_confirmed = True
    notification_user.confirm_content = confirm_content
    notification_user.confirmed_at = datetime.now(timezone.utc)
    notification_user.is_read = True
    crud.update_notification_user(db, notification_user)

    # Get shop info and order info if target_type is "order"
    shop_info = None
    order_info = None
    if notification.target_type == "order" and notification.target_id:
        order = get_order_by_id(db, str(notification.target_id))
        if order:
            order_info = _get_order_info(order)
            shop_info = _get_shop_info(db, order)

    return SuccessResponse(
        data=schemas.NotificationRead.build(
            notification, notification_user, shop_info, order_info
        )
    )


def delete_notification_service(notification_id: str, db):
    notification = crud.get_notification(db, notification_id)
    if not notification:
        raise notification_not_found()
    crud.delete_notification_user(db, notification_id)
    crud.delete_notification(db, notification)
    return SuccessResponse(data=None)


def get_notification_users_service(
    notification_id: str,
    db,
    limit: int = DEFAULT_LIMIT,
    offset: int = DEFAULT_OFFSET,
):
    """
    Get paginated notification_user records for a specific notification.

    Args:
        notification_id: ID of the notification
        db: Database session
        limit: Maximum number of records to return
        offset: Number of records to skip

    Returns:
        ListResponse with paginated notification_user records including user email and name
    """
    # Verify notification exists
    notification = crud.get_notification(db, notification_id)
    if not notification:
        raise notification_not_found()

    # Get paginated notification_users for this notification
    notification_users, total = crud.get_notification_users_by_notification_id(
        db, notification_id, limit=limit, offset=offset
    )

    # Convert to schema with user information
    notification_user_data = []
    for nu in notification_users:
        # Get user information
        user = get_user(db, nu.user_id)
        notification_user_data.append(
            schemas.NotificationUserRead(
                id=nu.id,
                notification_id=nu.notification_id,
                email=user.email if user else "",
                name=user.name if user else None,
            )
        )

    return ListResponse(
        limit=limit,
        offset=offset,
        total=total,
        data=notification_user_data,
    )
