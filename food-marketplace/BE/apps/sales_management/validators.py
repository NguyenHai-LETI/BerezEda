"""
Sales Management Validators

Validation functions for sales management operations.
Ensures data integrity and business rule compliance.
"""

from datetime import datetime
from typing import Optional

from .exceptions import invalid_date_range


def validate_date_range(
    date_from: Optional[datetime], date_to: Optional[datetime]
) -> None:
    """
    Validate date range parameters.

    Args:
        date_from: Start date
        date_to: End date

    Raises:
        HTTPException: If date range is invalid
    """
    if date_from and date_to and date_from > date_to:
        raise invalid_date_range()


def validate_shop_access(user, shop_id: Optional[str] = None) -> str:
    """
    Validate user has access to shop data.

    Args:
        user: User object
        shop_id: Optional specific shop ID to validate

    Returns:
        Shop ID the user has access to

    Raises:
        HTTPException: If user doesn't have shop access
    """
    from .exceptions import shop_access_required

    # Try to get shop ID from various sources
    user_shop_id = None

    # First priority: direct shop_id field (for staff members)
    if hasattr(user, "shop_id") and user.shop_id:
        user_shop_id = user.shop_id

    # Second priority: owned shop relationship (for shop owners)
    elif hasattr(user, "owned_shop") and user.owned_shop:
        if hasattr(user.owned_shop, "id"):
            user_shop_id = user.owned_shop.id
        elif isinstance(user.owned_shop, dict):
            user_shop_id = user.owned_shop.get("id")

    # Third priority: shop relationship (for staff or other cases)
    elif hasattr(user, "shop") and user.shop:
        if hasattr(user.shop, "id"):
            user_shop_id = user.shop.id
        elif isinstance(user.shop, dict):
            user_shop_id = user.shop.get("id")

    # Fourth priority: shops field (alternative naming)
    elif hasattr(user, "shops") and user.shops:
        if hasattr(user.shops, "id"):
            user_shop_id = user.shops.id
        elif isinstance(user.shops, dict):
            user_shop_id = user.shops.get("id")

    # Fallback: use get_associated_shop method if available
    elif hasattr(user, "get_associated_shop"):
        associated_shop = user.get_associated_shop()
        if associated_shop and hasattr(associated_shop, "id"):
            user_shop_id = associated_shop.id

    if not user_shop_id:
        raise shop_access_required()

    # If specific shop_id is provided, ensure user has access to it
    if shop_id and shop_id != user_shop_id:
        raise shop_access_required()

    return user_shop_id
