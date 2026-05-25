from typing import List, Optional

from sqlalchemy import or_
from sqlmodel import Session, desc, func, select

from apps.notifications.constants import SYSTEM_BROADCAST, USER_TARGETED
from apps.notifications.models.notification_users import NotificationUser
from apps.notifications.models.notifications import Notification


def get_notification(db: Session, notification_id: str):
    return db.get(Notification, notification_id)


def get_notifications(
    db: Session, limit: int = 20, offset: int = 0, search: Optional[str] = None
):
    """
    Get paginated notifications filtered by notification_type = SYSTEM_BROADCAST.

    Args:
        db: Database session
        limit: Maximum number of records to return
        offset: Number of records to skip
        search: Optional search term to filter by title or body (case-insensitive partial match)

    Returns:
        Tuple of (notifications list, total count)
    """
    # Base condition: notification_type = SYSTEM_BROADCAST
    conditions = [Notification.notification_type.in_([SYSTEM_BROADCAST, USER_TARGETED])]

    # Add search condition if provided
    if search:
        search_condition = or_(
            Notification.title.ilike(f"%{search}%"),
            Notification.body.ilike(f"%{search}%"),
        )
        conditions.append(search_condition)

    # Count total notifications
    count_statement = select(func.count()).select_from(Notification).where(*conditions)
    total = db.exec(count_statement).one()

    statement_noti = (
        select(Notification)
        .where(*conditions)
        .order_by(desc(Notification.created_at))
        .offset(max(offset, 0))
        .limit(limit)
    )

    notifications = db.exec(statement_noti).all()

    return notifications, total


def get_system_notifications(db: Session, limit: int = 20, offset: int = 0):
    """
    Get paginated notifications filtered by notification_type = SYSTEM_BROADCAST.

    Args:
        db: Database session
        limit: Maximum number of records to return
        offset: Number of records to skip

    Returns:
        Tuple of (notifications list, total count)
    """
    # Filter by notification_type = SYSTEM_BROADCAST
    condition = Notification.notification_type == SYSTEM_BROADCAST

    # Count total notifications
    count_statement = select(func.count()).select_from(Notification).where(condition)
    total = db.exec(count_statement).one()

    # Get paginated notifications
    statement_noti = (
        select(Notification)
        .where(condition)
        .order_by(desc(Notification.created_at))
        .offset(max(offset, 0))
        .limit(limit)
    )

    notifications = db.exec(statement_noti).all()

    return notifications, total


def get_notifications_for_user(
    db: Session, user_id: str, limit: int = 20, offset: int = 0
):
    """Return paginated notifications for a specific user (joins NotificationUser)."""
    # Count total notifications for user
    count_stmt = (
        select(func.count())
        .select_from(Notification)
        .join(NotificationUser)
        .where(NotificationUser.notification_id == Notification.id)
        .where(NotificationUser.user_id == user_id)
    )
    total = db.exec(count_stmt).one()

    stmt = (
        select(Notification)
        .join(NotificationUser)
        .where(NotificationUser.notification_id == Notification.id)
        .where(NotificationUser.user_id == user_id)
        .order_by(desc(Notification.created_at))
        .offset(offset)
        .limit(limit)
    )
    notifications = db.exec(stmt).all()
    return notifications, total


def create_notification(db: Session, notification: Notification):
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def update_notification(db: Session, notification: Notification):
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def update_notification_user(db: Session, notification_user: NotificationUser):
    db.add(notification_user)
    db.commit()
    db.refresh(notification_user)
    return notification_user


def delete_notification(db: Session, notification: Notification):
    db.delete(notification)
    db.commit()


def delete_notification_user(db: Session, notification_id: str):
    statement = select(NotificationUser).where(
        NotificationUser.notification_id == notification_id
    )
    records = db.exec(statement).all()
    for record in records:
        db.delete(record)
    db.commit()


def get_notification_user(db: Session, notification_id: str, user_id: str):
    statement = (
        select(NotificationUser)
        .where(NotificationUser.notification_id == notification_id)
        .where(NotificationUser.user_id == user_id)
    )
    return db.exec(statement).first()


def create_notification_user(db: Session, notification_user: NotificationUser):
    db.add(notification_user)
    db.commit()
    db.refresh(notification_user)
    return notification_user


def create_system_broadcast_notification(
    db: Session,
    title: str,
    body: str,
    created_by_id: str,
    notification_type: str = "info",
    db_notification_type: str = SYSTEM_BROADCAST,
) -> Notification:
    """
    Create a notification record.

    Args:
        db: Database session
        title: Notification title
        body: Notification body/content
        created_by_id: ID of the user creating the notification
        notification_type: Notification type (for 'type' field). Defaults to "info". Max length is 20 characters.
        db_notification_type: Notification type for database (SYSTEM_BROADCAST or USER_TARGETED). Defaults to SYSTEM_BROADCAST.

    Returns:
        Created Notification object

    Raises:
        ValueError: If notification_type exceeds 20 characters
    """
    # Validate notification_type length
    if len(notification_type) > 20:
        raise ValueError(
            f"notification_type must not exceed 20 characters. Got {len(notification_type)} characters: '{notification_type}'"
        )

    notification = Notification(
        title=title,
        body=body,
        type=notification_type,
        notification_type=db_notification_type,
        target_type="system",
        target_id=None,
        created_by_id=created_by_id,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def bulk_create_notification_users(
    db: Session,
    notification_id: str,
    user_ids: List[str],
) -> List[NotificationUser]:
    """
    Bulk create notification_user records for multiple users.

    Args:
        db: Database session
        notification_id: ID of the notification
        user_ids: List of user IDs to create notification_user records for

    Returns:
        List of created NotificationUser objects
    """
    notification_users = []
    for user_id in user_ids:
        notification_user = NotificationUser(
            notification_id=notification_id,
            user_id=user_id,
            channel=NotificationUser.PUSH,
            status=NotificationUser.PENDING,
        )
        notification_users.append(notification_user)

    db.add_all(notification_users)
    db.commit()
    return notification_users


def bulk_update_notification_user_status(
    db: Session,
    notification_users: List[NotificationUser],
    status: str,
):
    """
    Bulk update status for multiple notification_user records.

    Args:
        db: Database session
        notification_users: List of NotificationUser objects to update
        status: New status value
    """
    for nu in notification_users:
        nu.status = status
    db.commit()


def bulk_update_notification_users(
    db: Session,
    notification_users: List[NotificationUser],
    batch_size: int = 200,
):
    """
    Bulk update multiple notification_user records in batches.
    This is more efficient than committing each record individually.

    Args:
        db: Database session
        notification_users: List of NotificationUser objects to update
        batch_size: Number of records to commit per batch. Defaults to 200.
    """
    if not notification_users:
        return

    for i in range(0, len(notification_users), batch_size):
        batch = notification_users[i : i + batch_size]
        for nu in batch:
            db.add(nu)
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            raise e


def get_notification_users_by_notification_id(
    db: Session,
    notification_id: str,
    limit: int = 20,
    offset: int = 0,
) -> tuple[List[NotificationUser], int]:
    """
    Get paginated notification_user records for a specific notification.

    Args:
        db: Database session
        notification_id: ID of the notification
        limit: Maximum number of records to return
        offset: Number of records to skip

    Returns:
        Tuple of (list of NotificationUser objects, total count)
    """
    # Count total records
    count_statement = (
        select(func.count())
        .select_from(NotificationUser)
        .where(NotificationUser.notification_id == notification_id)
    )
    total = db.exec(count_statement).one()

    # Get paginated records
    statement = (
        select(NotificationUser)
        .where(NotificationUser.notification_id == notification_id)
        .offset(offset)
        .limit(limit)
    )
    notification_users = list(db.exec(statement).all())

    return notification_users, total


def get_notifications_by_created_by_id(
    db: Session,
    created_by_id: str,
    limit: int = 20,
    offset: int = 0,
    search: Optional[str] = None,
):
    """
    Get paginated notifications created by a specific user.

    Args:
        db: Database session
        created_by_id: ID of the user who created the notifications
        limit: Maximum number of records to return
        offset: Number of records to skip
        search: Optional search term to filter by title or body (case-insensitive partial match)

    Returns:
        Tuple of (notifications list, total count)
    """
    # Base conditions
    conditions = [
        Notification.created_by_id == created_by_id,
        Notification.notification_type.in_([SYSTEM_BROADCAST, USER_TARGETED]),
    ]
    # Add search condition if provided
    if search:
        search_condition = or_(
            Notification.title.ilike(f"%{search}%"),
            Notification.body.ilike(f"%{search}%"),
        )
        conditions.append(search_condition)

    # Count total notifications created by this user
    count_statement = select(func.count()).select_from(Notification).where(*conditions)
    total = db.exec(count_statement).one()

    statement = (
        select(Notification)
        .where(*conditions)
        .order_by(desc(Notification.created_at))
        .offset(offset)
        .limit(limit)
    )

    notifications = db.exec(statement).all()

    return notifications, total
