"""
Sales Management API Routers

FastAPI router endpoints for sales management functionality.
Provides endpoints for dashboard analytics, unsold/sold item listings,
and sales data filtering with Japanese UI support.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from apps.auth.permissions import ShopOwnerOrAdminUser
from apps.core.database import get_session
from apps.core.schemas import ListResponse, SuccessResponse

from . import schemas, services

router = APIRouter(tags=["Sales Management"])


def _validate_date_range_and_get_items(
    db: Session,
    user,
    service_function,
    limit: int,
    offset: int,
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    product_number: Optional[str],
    name: Optional[str],
    locker_name: Optional[str],
) -> ListResponse[schemas.SalesComboItem]:
    """
    Shared helper function to validate date range and get items.
    Reduces duplication between unsold-items and sold-items endpoints.
    """
    # Call the specific service function
    items, total = service_function(
        db=db,
        user=user,
        limit=limit,
        offset=offset,
        start_date=start_date,
        end_date=end_date,
        product_number=product_number,
        name=name,
        locker_name=locker_name,
    )

    return ListResponse(limit=limit, offset=offset, total=total, data=items)


@router.get("/dashboard", response_model=SuccessResponse[schemas.SalesDashboard])
def get_sales_dashboard(
    user: ShopOwnerOrAdminUser,
    db: Session = Depends(get_session),
    month: Optional[str] = Query(None, description="Month in YYYY-MM format"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    product_number: Optional[str] = Query(
        None, description="Filter by exact product number"
    ),
    name: Optional[str] = Query(
        None, description="Filter by product name (partial match)"
    ),
    locker_name: Optional[str] = Query(None, description="Filter by locker name"),
):
    """
    Get sales dashboard with analytics for the specified month.

    Returns comprehensive sales analytics including:
    - Unsold and sold item counts
    - Total revenue for the month
    - Status distribution
    - Recent activity metrics
    - Pending placement and expiring item counts
    """
    dashboard_data = services.get_sales_dashboard_service(
        db, user, month, start_date, end_date, product_number, name, locker_name
    )
    return SuccessResponse(data=dashboard_data)


@router.get("/unsold-items", response_model=ListResponse[schemas.SalesComboItem])
def get_unsold_items(
    user: ShopOwnerOrAdminUser,
    db: Session = Depends(get_session),
    limit: int = Query(20, ge=1, le=100, description="Number of items per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    start_date: Optional[datetime] = Query(
        None, description="Filter by created_at >= start_date"
    ),
    end_date: Optional[datetime] = Query(
        None, description="Filter by created_at <= end_date"
    ),
    product_number: Optional[str] = Query(
        None, description="Filter by exact product number"
    ),
    name: Optional[str] = Query(
        None, description="Filter by product name (partial match)"
    ),
    locker_name: Optional[str] = Query(None, description="Filter by locker name"),
):
    return _validate_date_range_and_get_items(
        db,
        user,
        services.get_unsold_items_service,
        limit,
        offset,
        start_date,
        end_date,
        product_number,
        name,
        locker_name,
    )


@router.get("/sold-items", response_model=ListResponse[schemas.SalesComboItem])
def get_sold_items(
    user: ShopOwnerOrAdminUser,
    db: Session = Depends(get_session),
    limit: int = Query(20, ge=1, le=100, description="Number of items per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    start_date: Optional[datetime] = Query(
        None, description="Filter by created_at >= start_date"
    ),
    end_date: Optional[datetime] = Query(
        None, description="Filter by created_at <= end_date"
    ),
    product_number: Optional[str] = Query(
        None, description="Filter by exact product number"
    ),
    name: Optional[str] = Query(
        None, description="Filter by product name (partial match)"
    ),
    locker_name: Optional[str] = Query(None, description="Filter by locker name"),
):
    return _validate_date_range_and_get_items(
        db,
        user,
        services.get_sold_items_service,
        limit,
        offset,
        start_date,
        end_date,
        product_number,
        name,
        locker_name,
    )
