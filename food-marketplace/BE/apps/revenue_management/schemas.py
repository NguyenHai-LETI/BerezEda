from typing import List, Optional, Union

from pydantic import BaseModel, Field, field_validator


class MonthRevenueData(BaseModel):
    """Revenue data for a specific month"""

    month: Union[str, int] = Field(description="Month number (1-12) or 'all'")
    sum_final_price: str = Field(
        description="Total final price for this month (formatted)"
    )

    @field_validator("sum_final_price", mode="before")
    def format_sum_final_price(cls, v):
        try:
            fv = float(v)
            if fv.is_integer():
                return f"{fv:,.0f}"
            return f"{fv:,.2f}"
        except Exception:
            return str(v)


class UnitRevenueData(BaseModel):
    """Revenue data for a specific unit"""

    sum_final_price: str = Field(
        description="Total final price for this unit (formatted)"
    )
    month: Union[str, int] = Field(description="Month number (1-12) or 'all'")

    @field_validator("sum_final_price", mode="before")
    def format_sum_final_price(cls, v):
        try:
            fv = float(v)
            if fv.is_integer():
                return f"{fv:,.0f}"
            return f"{fv:,.2f}"
        except Exception:
            return str(v)


class LockerUnitData(BaseModel):
    """Revenue data for a specific locker unit"""

    unit_id: str = Field(description="Unit identifier")
    unit_number: str = Field(description="Unit number")
    monthly_revenue: List[UnitRevenueData] = Field(description="Revenue data by month")


class LockerRevenueData(BaseModel):
    """Revenue data for a specific locker location"""

    locker_location_id: str = Field(description="Locker location identifier")
    name: str = Field(description="Locker location name")
    code: str = Field(description="Locker location code")
    monthly_revenue: List[MonthRevenueData] = Field(description="Revenue data by month")
    units: List[LockerUnitData] = Field(description="Revenue data by unit")


class RevenueDashboardData(BaseModel):
    monthly_revenue_all_locker: List[MonthRevenueData] = Field(
        description="Monthly revenue data for all lockers"
    )
    lockers: List[LockerRevenueData] = Field(description="Revenue data by locker")


class RevenueDashboardResponse(BaseModel):
    """Response schema for revenue dashboard API"""

    limit: int = Field(description="Number of items per page")
    offset: int = Field(description="Number of items to skip")
    total: int = Field(description="Total number of accessible locker locations")
    data: RevenueDashboardData = Field(description="Revenue dashboard data")


class RevenueManagementRequest(BaseModel):
    limit: Optional[int] = Field(default=20, description="Number of items per page")
    offset: Optional[int] = Field(default=0, description="Number of items to skip")
    duration: str = Field(description="Revenue dashboard duation")
    locker_id: Optional[List[str]] = Field(description="Filter by specific locker ID")


class RevenueSummary(BaseModel):
    """Summary of revenue data"""

    total_revenue: float = Field(description="Total revenue across all lockers")
    total_units: int = Field(description="Total number of units")
    total_lockers: int = Field(description="Total number of lockers")
    average_revenue_per_unit: float = Field(description="Average revenue per unit")
    average_revenue_per_locker: float = Field(description="Average revenue per locker")


class RevenueManagementSummaryResponse(BaseModel):
    """Response schema for revenue management summary API"""

    limit: int = Field(description="Number of items per page")
    offset: int = Field(description="Number of items to skip")
    total: int = Field(description="Total number of accessible locker locations")
    data: RevenueDashboardData = Field(description="Revenue dashboard data")
    summary: RevenueSummary = Field(description="Revenue summary statistics")


# ===== Shop revenue dashboard schemas =====


class ShopRevenueData(BaseModel):
    shop_id: str = Field(description="Shop identifier")
    shop_name: str = Field(description="Shop name")
    monthly_revenue: List[MonthRevenueData] = Field(description="Revenue by month")


class ShopRevenueDashboardData(BaseModel):
    monthly_revenue_all_shop: List[MonthRevenueData] = Field(
        description="Monthly revenue across selected shops"
    )
    shops: List[ShopRevenueData] = Field(
        description="Per-shop revenue data (paginated)"
    )


class ShopRevenueDashboardResponse(BaseModel):
    limit: int = Field(description="Number of items per page")
    offset: int = Field(description="Number of items to skip")
    total: int = Field(description="Total number of accessible shops")
    data: ShopRevenueDashboardData = Field(description="Shop revenue dashboard data")


class ShopRevenueGraphData(BaseModel):
    name: str = Field(description="Shop name")
    data: List[float] = Field(description="Shop revenue by duration")


class ShopRevenueGraphDataResponse(BaseModel):
    legend: List[str] = Field(description="List of shop name")
    xaxis: List[str] = Field(description="Duration")
    series: List[ShopRevenueGraphData] = Field(
        description="Revenue of shops by duration"
    )


class LockerRevenueGraphData(BaseModel):
    name: str = Field(description="Lockder name")
    data: List[float] = Field(description="Shop revenue by duration")


class LockerRevenueGraphDataResponse(BaseModel):
    legend: List[str] = Field(description="List of locker name")
    xaxis: List[str] = Field(description="Duration")
    series: List[LockerRevenueGraphData] = Field(
        description="Revenue of lockers by duration"
    )


class AgeGroupData(BaseModel):
    """Age group statistics data"""

    age_group: str = Field(description="Age group label")
    count: int = Field(description="Number of users in this age group")


class UserStatisticData(BaseModel):
    """User statistics by age group"""

    name: str = Field(description="Locker or shop name")
    data: List[Union[int, float]] = Field(
        description="User counts or revenue by age group"
    )


class UserStatisticGraphResponse(BaseModel):
    """Response for user statistics graph"""

    legend: List[str] = Field(description="List of locker/shop names")
    xaxis: List[str] = Field(description="Age group labels")
    series: List[UserStatisticData] = Field(description="User statistics by location")


class UserRetentionData(BaseModel):
    """User retention data for a shop"""

    name: str = Field(description="Shop name")
    data: List[float] = Field(description="Retention rate percentage")


class UserRetentionGraphResponse(BaseModel):
    """Response for user retention graph"""

    legend: List[str] = Field(description="List of shop names")
    series: List[UserRetentionData] = Field(description="Retention rate by shop")
