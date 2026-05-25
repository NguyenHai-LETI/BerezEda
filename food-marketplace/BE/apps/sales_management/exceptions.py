"""
Sales Management Exceptions

Custom exceptions for sales management functionality.
Provides consistent error handling for sales-related operations.
"""

from fastapi import HTTPException, status

# Error messages
SHOP_ACCESS_REQUIRED = "ショップアクセスが必要です。"
SALES_ITEM_NOT_FOUND = "販売アイテムが見つかりません。"
INVALID_STATUS_FILTER = "無効なステータスフィルターです。"
INVALID_DATE_RANGE = "無効な日付範囲です。"
ONLY_ONE_PARAM_ALLOWED = "Only one of month or start_date/end_date may be provided."


def shop_access_required():
    """Raise when user doesn't have shop access."""
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail=SHOP_ACCESS_REQUIRED
    )


def sales_item_not_found():
    """Raise when sales item is not found."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=SALES_ITEM_NOT_FOUND
    )


def invalid_status_filter(invalid_statuses: list, valid_statuses: list):
    """Raise when invalid status filter is provided."""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"無効なステータス: {invalid_statuses}. 有効なオプション: {valid_statuses}",
    )


def invalid_date_range():
    """Raise when invalid date range is provided."""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_DATE_RANGE
    )


def both_values_provided():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=ONLY_ONE_PARAM_ALLOWED
    )
