"""Exceptions for admin sales management module."""

from fastapi import HTTPException, status


def invalid_product_status(product_status: str, valid_values: set) -> HTTPException:
    """Raise exception for invalid product_status value."""
    valid_values_str = ", ".join(sorted(valid_values))
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Invalid product_status value: '{product_status}'. Valid values are: {valid_values_str}",
    )


def invalid_date_range() -> HTTPException:
    """Raise exception when start_date and end_date are not provided together."""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Both start_date and end_date must be provided together or both omitted.",
    )


def access_denied_to_shops(invalid_shops: set) -> HTTPException:
    """Raise exception when user tries to access shops they don't have permission for."""
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Access denied to shops: {', '.join(invalid_shops)}",
    )


def access_denied_to_locker_locations(invalid_locations: set) -> HTTPException:
    """Raise exception when user tries to access locker locations they don't have permission for."""
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Access denied to locker locations: {', '.join(invalid_locations)}",
    )
