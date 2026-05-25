"""Schemas for admin sales management APIs."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class AccessibleShop(BaseModel):
    """Minimal shop representation for admin-facing dropdowns."""

    id: str
    name: Optional[str] = None
    code: Optional[str] = None

    model_config = {"from_attributes": True}


class DashboardStaticData(BaseModel):
    """Static data for dashboard summary."""

    total_sales_revenue: str
    total_foodloss_reduced: str
    total_co2_reduced: str
    total_sold_products_non_donated: str
    total_sold_products_donated: str
    total_unsold_products: str


class DashboardComboData(BaseModel):
    """Combo data for dashboard listing."""

    id: str
    product_number: Optional[str] = None
    combo_name: str
    combo_status: str
    status: str
    is_free: bool
    discount_percentage: float
    original_price: Optional[float] = None
    order_status: Optional[str] = None
    foodloss: float
    co2_reduced: float
    sale_duration: Optional[str] = None
    item_deposit_at: Optional[datetime] = None
    sale_end_time: Optional[datetime] = None
    locker_unit_id: Optional[str] = None
    unit_number: Optional[str] = None
    locker_name: Optional[str] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    user_phone: Optional[str] = None
    shop_name: Optional[str] = None
    sale_price: Optional[float] = None
    final_price: Optional[float] = None
    completed_at: Optional[datetime] = None
    picked_up_at: Optional[datetime] = None


class DashboardResponse(BaseModel):
    """Dashboard response with static data and combo list."""

    limit: int
    offset: int
    total: int
    static_data: DashboardStaticData
    combo_data: List[DashboardComboData]


class ComboMatchingCountByDate(BaseModel):
    """Combo matching count for a specific locker on a specific date."""

    locker_id: str
    locker_name: str
    date: str  # YYYY-MM-DD format
    count: int


class ComboMatchingStatsResponse(BaseModel):
    """Response for combo matching statistics by locker and date."""

    dates: List[str]  # List of dates in YYYY-MM-DD format
    lockers: List[dict]  # List of {id, name, counts_by_date: {date: count}}
