from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from apps.auth.permissions import (
    AuthenticatedUser,
    AuthenticatedUserOrNone,
    LockerOwnerOrAdminUser,
)
from apps.core.database import get_session
from apps.core.schemas import ListResponse, SuccessResponse
from apps.notifications import schemas, validators
from apps.notifications.services import notification_crud as services
from apps.notifications.services.push_notification import (
    get_user_ids_from_filters,
    send_push_notification_to_users,
)

router = APIRouter(tags=["Notifications"])


@router.get("/", response_model=ListResponse[schemas.NotificationRead])
def list_notifications(
    user: AuthenticatedUserOrNone,
    db: Session = Depends(get_session),
    limit: int = 20,
    offset: int = 0,
):
    # Return only notifications for the authenticated user
    return services.list_notifications_service(
        db, user=user, limit=limit, offset=offset
    )


@router.get("/admin", response_model=ListResponse[schemas.NotificationRead])
def list_admin_notifications(
    user: LockerOwnerOrAdminUser,
    db: Session = Depends(get_session),
    limit: int = 20,
    offset: int = 0,
    search: Optional[str] = Query(
        None,
        description="Search in notification title or body (case-insensitive partial match)",
    ),
):
    """
    Get notifications based on user role:
    - If admin: returns ALL notifications in the database with created_by_role field
    - If owner_locker: returns only notifications created by the current user

    Returns paginated list of notifications.
    """
    return services.list_admin_notifications_service(
        db, user=user, limit=limit, offset=offset, search=search
    )


@router.post("/", response_model=SuccessResponse[schemas.NotificationRead])
def create_notification(
    notification: schemas.NotificationCreate,
    user: AuthenticatedUser,
    db: Session = Depends(get_session),
):
    return services.create_notification_service(notification, db)


@router.get(
    "/{notification_id}/users",
    response_model=ListResponse[schemas.NotificationUserRead],
    summary="Get all notification users for a notification",
    description="Get paginated notification_user records associated with a specific notification",
)
def get_notification_users(
    notification_id: str,
    user: AuthenticatedUser,
    db: Session = Depends(get_session),
    limit: int = 20,
    offset: int = 0,
):
    """
    Get paginated notification_user records for a specific notification.

    Returns a paginated list of users who received this notification.
    """
    return services.get_notification_users_service(
        notification_id, db, limit=limit, offset=offset
    )


@router.get(
    "/public/{notification_id}",
    response_model=SuccessResponse[schemas.NotificationRead],
)
def get_public_notification(notification_id: str, db: Session = Depends(get_session)):
    """
    Get notification by ID (public endpoint, no authentication required).

    Returns the notification record from the database.
    """
    return services.get_public_notification_service(notification_id, db)


@router.get(
    "/{notification_id}", response_model=SuccessResponse[schemas.NotificationRead]
)
def get_notification(
    notification_id: str, user: AuthenticatedUser, db: Session = Depends(get_session)
):
    return services.get_notification_service(user, notification_id, db)


@router.put(
    "/{notification_id}/confirm",
    response_model=SuccessResponse[schemas.NotificationRead],
)
def confirm_notification(
    notification_id: str,
    request: schemas.NotificationConfirmRequest,
    user: AuthenticatedUser,
    db: Session = Depends(get_session),
):
    """
    Confirm a notification with user's response (e.g., product expiry reached).
    Saves confirm_content, sets is_confirmed=True and confirmed_at.
    """
    return services.confirm_notification_service(
        notification_id, user, request.confirm_content, db
    )


@router.put(
    "/{notification_id}", response_model=SuccessResponse[schemas.NotificationRead]
)
def update_notification(
    notification_id: str,
    update_data: schemas.NotificationUpdate,
    user: AuthenticatedUser,
    db: Session = Depends(get_session),
):
    return services.update_notification_service(
        notification_id, user, update_data.confirm_content, db
    )


@router.delete("/{notification_id}", response_model=SuccessResponse)
def delete_notification(
    notification_id: str,
    user: AuthenticatedUser,
    db: Session = Depends(get_session),
):
    return services.delete_notification_service(notification_id, db)


@router.post(
    "/push",
    response_model=SuccessResponse[schemas.PushNotificationResponse],
    summary="Send push notification to multiple users",
    description="""
    Send push notification to multiple users by their user IDs or by filter criteria.
    
    This endpoint allows admin users to send push notifications to a list of users.
    The notification will be sent to all devices registered for each user.
    
    You can either:
    1. Specify user_ids directly in the request body
    2. Use filter parameters (permission, email, phone, birthday, town, gender) to filter users
    
    Note: Cannot use both user_ids and filter parameters at the same time.
    
    Returns statistics about the sending process including:
    - Total number of users
    - Number of successful sends
    - Number of failed sends
    - List of user IDs that failed
    """,
)
def send_push_notification(
    request: schemas.PushNotificationRequest,
    user: LockerOwnerOrAdminUser,
    db: Session = Depends(get_session),
    permission: Optional[List[str]] = Query(
        None, description="Filter users by multiple permissions"
    ),
    email: Optional[str] = Query(
        None, description="Email value to filter (partial match, case-insensitive)"
    ),
    is_not_email: Optional[str] = Query(None, description="Email value to exclude"),
    phone_number: Optional[str] = Query(None, description="Phone value to filter"),
    is_not_phone_number: Optional[str] = Query(
        None, description="Phone value to exclude"
    ),
    e_birthday: Optional[str] = Query(
        None, description="Birthday value in YYYY-MM-DD format"
    ),
    is_not_birthday: Optional[str] = Query(
        None, description="Birthday value in YYYY-MM-DD format to exclude"
    ),
    lte_birthday: Optional[str] = Query(
        None,
        description="Filter birthday < lte_birthday (YYYY-MM-DD format). Can be used alone or with gte_birthday for range.",
    ),
    gte_birthday: Optional[str] = Query(
        None,
        description="Filter birthday > gte_birthday (YYYY-MM-DD format). Can be used alone or with lte_birthday for range.",
    ),
    town: Optional[str] = Query(None, description="Town name to search in address"),
    gender: Optional[str] = Query(None, description="Gender filter: male or female"),
):
    """
    Send push notification to multiple users.

    Args:
        request: PushNotificationRequest containing user_ids (optional if filters are used), title, and body
        user: Authenticated admin user or owner_locker
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
        SuccessResponse with PushNotificationResponse containing sending statistics
    """
    # Get user_ids from filters if any filter parameters are provided
    user_ids_from_filters, has_filters = get_user_ids_from_filters(
        db=db,
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

    # Use user_ids from filters if available, otherwise use from request
    user_ids = user_ids_from_filters if has_filters else request.user_ids

    # Validate push notification request
    validators.validate_push_notification_request(
        request=request,
        has_filters=has_filters,
        user_ids_from_filters=user_ids_from_filters,
    )

    result = send_push_notification_to_users(
        db=db,
        user_ids=user_ids,
        title=request.title,
        content=request.body,
        created_by_id=str(user.id),
        push_to_all=request.push_to_all,
        notification_type=request.from_represent,
    )
    return SuccessResponse(data=result)
