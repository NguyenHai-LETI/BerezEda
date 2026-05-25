from typing import List, Optional

from fastapi import HTTPException

from apps.notifications.schemas import PushNotificationRequest


def validate_push_notification_request(
    request: PushNotificationRequest,
    has_filters: bool,
    user_ids_from_filters: Optional[List[str]] = None,
):
    """
    Validate push notification request based on filters and user_ids.

    Args:
        request: PushNotificationRequest object
        has_filters: Whether any filter parameters are provided
        user_ids_from_filters: List of user_ids obtained from filters (if filters were used)

    Raises:
        HTTPException: If validation fails
    """
    # Validate: cannot use both user_ids and filters
    if has_filters and request.user_ids:
        raise HTTPException(
            status_code=400,
            detail="Cannot specify both user_ids and filter parameters. Use either user_ids or filters, not both.",
        )

    # If filters were used, validate that users were found
    if has_filters:
        if not user_ids_from_filters or len(user_ids_from_filters) == 0:
            raise HTTPException(
                status_code=400,
                detail="No users found matching the provided filter criteria.",
            )

    # Validate user_ids if no filters (keep original validation logic)
    if not has_filters and not request.push_to_all:
        if not request.user_ids or len(request.user_ids) == 0:
            raise HTTPException(
                status_code=400,
                detail="user_ids is required and cannot be empty when push_to_all is False and no filters are provided.",
            )
