"""
Sales Management Schemas

Pydantic models for sales management API requests and responses.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SalesComboItem(BaseModel):
    """Enhanced combo item for sales management UI following sold_spec.md Section 7"""

    # Basic combo info
    id: str
    name: str
    description: Optional[str] = None
    product_code: Optional[str] = Field(
        None, description="Product number/code (商品コード)"
    )
    status: str

    # Pricing info
    final_price: Optional[float] = None
    original_price: Optional[float] = None
    discount_price: Optional[float] = None
    discount_percentage: float = 0
    is_free: bool = False
    order_status: Optional[str] = None

    # Time information (Section 7.1 & 7.2 - Date and time when user received item)
    created_at: datetime
    listing_end_date: Optional[datetime] = None

    # Countdown timers (calculated fields)
    placement_countdown_seconds: Optional[int] = Field(
        None, description="Seconds remaining for locker placement"
    )
    placement_countdown_display: Optional[str] = Field(
        None, description="Formatted countdown display (HH:MM:SS)"
    )

    # Locker info (Section 7.1 & 7.2 - Locker name and number)
    locker_location_name: Optional[str] = Field(None, description="ロッカー名")
    locker_unit_number: Optional[str] = Field(None, description="ロッカーNo.")
    locker_location_id: Optional[str] = None

    # Status display (calculated fields)
    status_display_text: str = Field(description="Localized status text for UI")

    # Display time (formatted for UI)
    display_time: Optional[str] = Field(
        None, description="Formatted time for UI (end time, purchase time, etc.)"
    )
    display_time_label: Optional[str] = Field(
        None, description="Label for the display time"
    )
    model_config = {"from_attributes": True}


class SalesDashboard(BaseModel):
    """Sales dashboard summary data following sold_spec.md requirements"""

    # Food Loss Banner (Section 2)
    food_loss_this_month_grams: int = Field(
        description="Food loss reduction this month in grams"
    )
    food_loss_last_month_grams: int = Field(
        description="Food loss reduction last month in grams"
    )

    # Monthly Support and Revenue (Section 5)
    support_count_this_month: int = Field(
        description="Number of sold items this month (今月支援)"
    )
    total_revenue_this_month: float = Field(description="Total revenue this month")

    # Additional dashboard metrics
    unsold_count_this_month: int = Field(
        description="Number of unsold items this month"
    )
    sold_count_this_month: int = Field(description="Number of sold items this month")
    donation_count_this_month: int = Field(
        description="Number of donation items this month"
    )

    # Status distribution
    status_counts: dict = Field(description="Count of items by status")

    # Recent activity summary
    recent_sales_count: int = Field(description="Sales in last 24 hours")
    pending_placement_count: int = Field(description="Items pending locker placement")
    expiring_soon_count: int = Field(description="Items expiring within 2 hours")

    model_config = {"from_attributes": True}


class SalesAnalytics(BaseModel):
    """Detailed sales analytics data"""

    # Time period
    period_start: datetime
    period_end: datetime

    # Sales metrics
    total_sales: int
    total_revenue: float
    average_sale_price: float

    # Product metrics
    total_products_listed: int
    total_products_sold: int
    sell_through_rate: float = Field(description="Percentage of products sold")

    # Donation metrics
    total_donations: int
    donation_rate: float = Field(description="Percentage of items donated")

    # Time-based metrics
    average_time_to_sell: Optional[float] = Field(
        None, description="Average time to sell in hours"
    )
    expired_items: int
    cancelled_items: int

    model_config = {"from_attributes": True}
