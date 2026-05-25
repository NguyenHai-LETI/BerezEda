from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from apps.auth.permissions import (
    AdminUser,
    LockerOwnerOrAdminUser,
    ShopLockerOwnerOrAdminUser,
)
from apps.core.database import get_session
from apps.core.schemas import SuccessResponse
from apps.revenue_management import services
from apps.revenue_management.services import get_accessible_locker_location_service

router = APIRouter(tags=["Revenue Management"])


@router.get("/dashboard/", response_model=SuccessResponse)
def get_revenue_dashboard(
    user: ShopLockerOwnerOrAdminUser,
    db: Session = Depends(get_session),
    duration: Optional[str] = Query(
        None,
        description="defined option like FIRST_HALF_THIS_YEAR, SECOND_HALF_THIS_YEAR, etc.",
    ),
    locker_location_ids: Optional[List[str]] = Query(
        None, description="Filter by multiple locker locations"
    ),
    limit: int = Query(20, description="Number of items per page"),
    offset: int = Query(0, description="Number of items to skip"),
):

    response = services.get_revenue_dashboard_data(
        db=db,
        user=user,
        duration=duration,
        location_ids=locker_location_ids,
        limit=limit,
        offset=offset,
    )

    return SuccessResponse(data=response)


@router.get("/dashboard/shop-revenue", response_model=SuccessResponse)
def get_revenue_dashboard(
    user: AdminUser,
    db: Session = Depends(get_session),
    duration: Optional[str] = Query(
        None,
        description="defined option like FIRST_HALF_THIS_YEAR, SECOND_HALF_THIS_YEAR, etc.",
    ),
    shop_ids: Optional[List[str]] = Query(None, description="Filter by multiple shops"),
    limit: int = Query(20, description="Number of items per page"),
    offset: int = Query(0, description="Number of items to skip"),
):

    response = services.get_shop_revenue_dashboard_data(
        db=db,
        duration=duration,
        shop_ids=shop_ids,
        limit=limit,
        offset=offset,
    )

    return SuccessResponse(data=response)


@router.get("/accessible-locations", response_model=SuccessResponse)
def get_accessible_locker_locations(
    user: ShopLockerOwnerOrAdminUser,
    db: Session = Depends(get_session),
    locker_name: Optional[str] = Query(None),
):
    all_locker_location, total_all_locations = get_accessible_locker_location_service(
        db=db, user=user, locker_name=locker_name
    )
    return SuccessResponse(data=all_locker_location)


@router.get("/accessible-shop/by-locations", response_model=SuccessResponse)
def get_accessible_shops_by_locations(
    user: LockerOwnerOrAdminUser,
    db: Session = Depends(get_session),
    location_ids: List[str] = Query(..., description="Filter by locker location IDs"),
):
    """
    Get accessible shops by locker location IDs.

    Returns list of shops with id and name that are associated with the given locker locations.
    """
    shops = services.get_accessible_shops_by_locations_service(
        db=db, location_ids=location_ids
    )
    return SuccessResponse(data={"shops": shops})


@router.get("/dashboard/graph/shop/revenue", response_model=SuccessResponse)
def get_revenue_graph_by_shop(
    user: LockerOwnerOrAdminUser,
    db: Session = Depends(get_session),
    duration: str = Query(
        description="defined option like FIRST_HALF_THIS_YEAR, SECOND_HALF_THIS_YEAR, QUARTERS_THIS_YEAR, MONTHS_THIS_YEAR, WEEKS_THIS_MONTH, TODAY.",
    ),
    shop_ids: List[str] = Query(description="Filter by multiple shops"),
):
    response = services.get_revenue_graph_by_shop_data(
        db=db,
        duration=duration,
        shop_ids=shop_ids,
    )

    return SuccessResponse(data=response)


@router.get("/dashboard/graph/locker/revenue", response_model=SuccessResponse)
def get_revenue_graph_by_locker(
    user: LockerOwnerOrAdminUser,
    db: Session = Depends(get_session),
    duration: str = Query(
        description="defined option like FIRST_HALF_THIS_YEAR, SECOND_HALF_THIS_YEAR, QUARTERS_THIS_YEAR, MONTHS_THIS_YEAR, WEEKS_THIS_MONTH, TODAY.",
    ),
    locker_ids: List[str] = Query(description="Filter by multiple lockers"),
):
    response = services.get_revenue_graph_by_locker_data(
        db=db,
        user=user,
        duration=duration,
        locker_ids=locker_ids,
    )

    return SuccessResponse(data=response)


@router.get("/dashboard/graph/age-group/statistic", response_model=SuccessResponse)
def get_age_group_statistics_graph(
    user: LockerOwnerOrAdminUser,
    db: Session = Depends(get_session),
    duration: str = Query(
        description="defined option like FIRST_HALF_THIS_YEAR, SECOND_HALF_THIS_YEAR, THIS_QUARTER (quý này), THIS_MONTH (tháng này), THIS_WEEK (tuần này), TODAY (hôm nay).",
    ),
    metric: str = Query(
        description="CUSTOMER_COUNT or REVENUE",
    ),
    locker_ids: Optional[List[str]] = Query(None, description="Filter by locker IDs"),
    shop_ids: Optional[List[str]] = Query(None, description="Filter by shop IDs"),
):
    """
    Get age group statistics by customer count or revenue.

    Duration options:
    - FIRST_HALF_THIS_YEAR: First half of this year (Jan-Jun)
    - SECOND_HALF_THIS_YEAR: Second half of this year (Jul-Dec)
    - THIS_QUARTER: Current quarter only (Q1: Jan-Mar, Q2: Apr-Jun, Q3: Jul-Sep, Q4: Oct-Dec)
    - THIS_MONTH: Current month only
    - THIS_WEEK: Current week only (Monday to Sunday)
    - TODAY: Today only

    Metrics:
    - CUSTOMER_COUNT: Count unique users by age group
    - REVENUE: Sum revenue (order.final_price) by age group

    Age groups:
    - Under 20 (20歳未満)
    - 20-29 (20-29歳)
    - 30-39 (30-39歳)
    - 40-49 (40-49歳)
    - 50-59 (50-59歳)
    - 60 and above (60歳以上)

    Must provide either locker_ids or shop_ids (not both).
    """
    response = services.get_user_statistics_graph_data(
        db=db,
        user=user,
        duration=duration,
        metric=metric,
        locker_ids=locker_ids,
        shop_ids=shop_ids,
    )

    return SuccessResponse(data=response)


@router.get("/dashboard/graph/user-retention", response_model=SuccessResponse)
def get_user_retention_graph(
    user: LockerOwnerOrAdminUser,
    db: Session = Depends(get_session),
    duration: str = Query(
        description="defined option like FIRST_HALF_THIS_YEAR, SECOND_HALF_THIS_YEAR, THIS_QUARTER (quý này), THIS_MONTH (tháng này), THIS_WEEK (tuần này), TODAY (hôm nay).",
    ),
    segment: str = Query(
        description="ONE_TIME or RETURNING",
    ),
    shop_ids: List[str] = Query(..., description="Filter by shop IDs"),
):
    """
    Get user retention statistics by shop.

    Duration options:
    - FIRST_HALF_THIS_YEAR: First half of this year (Jan-Jun)
    - SECOND_HALF_THIS_YEAR: Second half of this year (Jul-Dec)
    - THIS_QUARTER: Current quarter only (Q1: Jan-Mar, Q2: Apr-Jun, Q3: Jul-Sep, Q4: Oct-Dec)
    - THIS_MONTH: Current month only
    - THIS_WEEK: Current week only (Monday to Sunday)
    - TODAY: Today only

    Segments:
    - ONE_TIME: Customers with exactly 1 successful order
      Formula: (Customers with 1 order / Total customers with >=1 order) × 100

    - RETURNING: Customers with 2 or more successful orders
      Formula: (Customers with >=2 orders / Total customers with >=1 order) × 100

    Returns retention rate percentage for each shop.
    """
    response = services.get_user_retention_graph_data(
        db=db,
        duration=duration,
        segment=segment,
        shop_ids=shop_ids,
    )

    return SuccessResponse(data=response)


@router.get("/dashboard/export-csv")
def export_dashboard_csv(
    user: LockerOwnerOrAdminUser,
    db: Session = Depends(get_session),
    shop_ids: Optional[List[str]] = Query(None, description="Filter by shop IDs"),
    locker_location_ids: Optional[List[str]] = Query(
        None, description="Filter by locker location IDs"
    ),
    start_date: Optional[datetime] = Query(
        None, description="Filter by start date (JST)"
    ),
    end_date: Optional[datetime] = Query(None, description="Filter by end date (JST)"),
):
    """
    Export dashboard data as CSV file.

    Returns CSV file with data grouped by locker location and shop.
    Includes metrics:
    - Total sold products
    - Sold products (donated)
    - Sold products (non-donated)
    - Unsold products
    - Total revenue

    - Admin users can access all shops and locker locations
    - Locker owners can only access shops and locker locations they own
    """
    csv_content, filename = services.generate_csv_export_service(
        db=db,
        user=user,
        shop_ids=shop_ids,
        locker_location_ids=locker_location_ids,
        start_date=start_date,
        end_date=end_date,
    )

    # Return CSV file as streaming response
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
