"Admin Sales Management API routers."

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from apps.auth.permissions import AuthenticatedUser, LockerOwnerOrAdminUser
from apps.core.database import get_session
from apps.core.schemas import SuccessResponse

from . import schemas, services
from .constants import (
    PRODUCT_STATUS_EXPIRED,
    PRODUCT_STATUS_SELLING,
    PRODUCT_STATUS_SELLING_DONATION_PHASE,
    PRODUCT_STATUS_SOLD_DONATION,
    PRODUCT_STATUS_SOLD_PICKED_UP,
    PRODUCT_STATUS_SOLD_READY_FOR_PICK_UP,
)

router = APIRouter(tags=["Admin Sales Management"])


@router.get(
    "/accessible-shop",
    response_model=SuccessResponse[list[schemas.AccessibleShop]],
)
def get_accessible_shops(user: AuthenticatedUser, db: Session = Depends(get_session)):
    """
    Get shops accessible for admin sales management filters.

    - Admin users receive all active shops
    - Locker owners receive shops linked to their locker locations
    """
    shops = services.get_accessible_shops_service(db, user)
    return SuccessResponse(data=shops)


@router.get(
    "/dashboard",
    response_model=SuccessResponse[schemas.DashboardResponse],
)
def get_dashboard(
    user: AuthenticatedUser,
    db: Session = Depends(get_session),
    search_text: Optional[str] = Query(
        None, description="Search by combo name or user name"
    ),
    shop_ids: Optional[List[str]] = Query(None, description="Filter by shop IDs"),
    locker_location_ids: Optional[List[str]] = Query(
        None, description="Filter by locker location IDs"
    ),
    product_status: Optional[str] = Query(
        None,
        description=f"Filter by product status: {PRODUCT_STATUS_SELLING}, {PRODUCT_STATUS_SELLING_DONATION_PHASE}, {PRODUCT_STATUS_SOLD_DONATION}, {PRODUCT_STATUS_SOLD_PICKED_UP}, {PRODUCT_STATUS_SOLD_READY_FOR_PICK_UP}, {PRODUCT_STATUS_EXPIRED}",
    ),
    start_date: Optional[datetime] = Query(
        None, description="Filter by created_at start date"
    ),
    end_date: Optional[datetime] = Query(
        None, description="Filter by created_at end date"
    ),
    limit: int = Query(20, ge=1, le=100, description="Number of items per page"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
):
    """
    Get dashboard data with filtering and aggregation.

    - Admin users can access all shops and locker locations
    - Locker owners can only access shops and locker locations they own
    - Default filter: is_available = True
    """
    result = services.get_dashboard_service(
        db=db,
        user=user,
        search_text=search_text,
        shop_ids=shop_ids,
        locker_location_ids=locker_location_ids,
        product_status=product_status,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    return SuccessResponse(data=result)


@router.get(
    "/combo-matching-stats",
    response_model=SuccessResponse[schemas.ComboMatchingStatsResponse],
)
def get_combo_matching_stats(
    user: LockerOwnerOrAdminUser,
    db: Session = Depends(get_session),
    start_date: datetime = Query(..., description="Start date (inclusive)"),
    end_date: datetime = Query(..., description="End date (inclusive)"),
    locker_ids: List[str] = Query(..., description="List of locker location IDs"),
    include_support_combos: bool = Query(
        True, description="Include orders with final_price = 0 (support combos)"
    ),
    include_nonsupport_combos: bool = Query(
        True, description="Include orders with final_price != 0 (non-support combos)"
    ),
):
    """
    Get combo matching statistics by locker and date.
    Order status considered: PICKED_UP, READY_FOR_PICKUP
    """
    result = services.get_combo_matching_stats_service(
        db=db,
        start_date=start_date,
        end_date=end_date,
        locker_ids=locker_ids,
        include_support_combos=include_support_combos,
        include_nonsupport_combos=include_nonsupport_combos,
    )
    return SuccessResponse(data=result)
