from datetime import datetime
from typing import List, Optional

from apps.revenue_management.exceptions import total_mismatch_exception


def validate_revenue_all_lockers(revenue: List):
    all_month_total = next(value for month, value in revenue if month == "all_months")
    sum_other_months = sum(value for month, value in revenue if month != "all_months")
    if all_month_total != sum_other_months:
        raise total_mismatch_exception()
    return True


def validate_date_range(
    start_date: Optional[datetime], end_date: Optional[datetime]
) -> bool:
    """
    Validate that start_date and end_date are both provided or both omitted.

    Args:
        start_date: Optional start date
        end_date: Optional end date

    Returns:
        True if valid

    Raises:
        HTTPException: If only one date is provided
    """
    from apps.admin_sales_management.exceptions import invalid_date_range

    if (start_date is None) != (end_date is None):
        raise invalid_date_range()
