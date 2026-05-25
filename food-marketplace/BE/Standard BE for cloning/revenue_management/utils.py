"""Utility functions for revenue management."""

from datetime import datetime
from typing import Optional


def format_japanese_date(date: datetime) -> str:
    """
    Format datetime to Japanese date format.

    Example: 2025年12月31日

    Args:
        date: Datetime object

    Returns:
        Formatted Japanese date string
    """
    return f"{date.year}年{date.month}月{date.day}日"


def format_currency(amount: float) -> str:
    """
    Format currency with comma separators.

    Example: 1234567.89 -> "1,234,568"

    Args:
        amount: Amount to format

    Returns:
        Formatted currency string
    """
    return f"{int(round(amount)):,}"


def generate_csv_filename(
    start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
) -> str:
    """
    Generate CSV filename based on date range.

    Args:
        start_date: Optional start date
        end_date: Optional end date

    Returns:
        CSV filename
    """
    if start_date and end_date:
        return f"dashboard_export_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
    return f"dashboard_export_{datetime.now().strftime('%Y%m%d')}.csv"
