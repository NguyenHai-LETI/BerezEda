from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from apps.auth.permissions import (
    AuthenticatedUser,
    AuthenticatedUserOrNone,
    ShopOwnerOrAdminUser,
)
from apps.core.database import get_session
from apps.core.schemas import ListResponse, SuccessResponse

from . import schemas, services

router = APIRouter(tags=["Shops"])


@router.get("/", response_model=ListResponse[schemas.ShopRead])
def list_shops(
    user: AuthenticatedUser,
    db: Session = Depends(get_session),
    limit: int = 20,
    offset: int = 0,
    name: Optional[str] = Query(None, description="Filter shops by name"),
):
    shops, total = services.list_shops_service(
        user, db, limit=limit, offset=offset, name=name
    )
    return ListResponse(limit=limit, offset=offset, total=total, data=shops)


@router.get("/my-shop", response_model=SuccessResponse[schemas.ShopRead])
def get_my_shop(user: ShopOwnerOrAdminUser, db: Session = Depends(get_session)):
    """
    Get my shop information based on logged-in user's shop code.
    Only accessible by admin, owner_shop, and staff_shop roles.
    """
    shop_obj = services.get_my_shop_service(user, db)
    return SuccessResponse(data=shop_obj)


@router.get("/{shop_id}", response_model=SuccessResponse[schemas.ShopRead])
def get_shop(
    shop_id: str, user: AuthenticatedUserOrNone, db: Session = Depends(get_session)
):
    shop_obj = services.get_shop_service(shop_id, user, db)
    return SuccessResponse(data=shop_obj)


@router.get("/{shop_id}/combos", response_model=ListResponse[schemas.ShopComboRead])
def get_shop_combos(
    shop_id: str,
    user: AuthenticatedUserOrNone,
    db: Session = Depends(get_session),
    limit: int = 20,
    offset: int = 0,
    is_selling: Optional[bool] = Query(
        None, description="Filter combos by selling status"
    ),
):
    """Get all combos for a specific shop with optional selling filter."""
    combos, total = services.get_shop_combos_service(
        shop_id,
        db,
        user=user,
        limit=limit,
        offset=offset,
        is_selling=is_selling,
    )
    return ListResponse(limit=limit, offset=offset, total=total, data=combos)


@router.get(
    "/my-shop/sales-history",
    response_model=ListResponse[schemas.SalesHistoryRead],
)
def get_my_shop_sales_history(
    date: str,
    user: ShopOwnerOrAdminUser,
    db: Session = Depends(get_session),
    limit: int = 20,
    offset: int = 0,
):
    """
    Get sales history for the current user's shop filtered by date.
    Only accessible by shop owners (uses their own shop automatically).

    Args:
        date: Target date in YYYY-MM-DD format
        user: Authenticated shop owner
        db: Database session

    Returns:
        List of sales history records for the specified date
    """
    # Use the user's associated shop ID
    associated_shop = user.get_associated_shop()
    if not associated_shop:
        raise HTTPException(status_code=404, detail="No shop associated with this user")

    sales_history, total = services.get_shop_sales_history_service(
        associated_shop.id, date, user, db, limit, offset
    )
    return ListResponse(limit=limit, offset=offset, total=total, data=sales_history)


@router.patch("/contact", response_model=SuccessResponse[schemas.ShopRead])
def update_shop_contact(
    shop_update: schemas.ShopPartialUpdate,
    user: ShopOwnerOrAdminUser,
    db: Session = Depends(get_session),
):
    """
    Update only phone and description fields of the current user's shop.
    Only admin or shop owner can update these fields.
    """
    shop_obj = services.update_shop_contact_service(shop_update, user, db)
    return SuccessResponse(data=shop_obj)


@router.delete("/{shop_id}", response_model=SuccessResponse)
def delete_shop(
    shop_id: str,
    user: ShopOwnerOrAdminUser,
    db: Session = Depends(get_session),
):
    """
    Soft delete a shop and all associated users.
    Only admin or shop owner can delete the shop.
    """
    services.delete_shop_service(shop_id, db, user)
    return SuccessResponse(data=None)


@router.post("/sync-analytics", response_model=SuccessResponse)
def sync_all_shops_analytics(
    user: AuthenticatedUser,
    db: Session = Depends(get_session),
):
    """
    Manually trigger analytics sync for all shops to Firebase.
    Only admin users can trigger this.
    """
    if user.permissions != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    count = services.sync_all_shops_analytics_to_firebase(db)
    return SuccessResponse(
        data={"message": f"Analytics sync triggered for {count} shops"}
    )


@router.get(
    "/location/{location_id}",
    response_model=ListResponse[schemas.ShopReadWithDistance],
)
def get_shops_by_location(
    location_id: str,
    user: AuthenticatedUserOrNone,
    db: Session = Depends(get_session),
    limit: int = 20,
    offset: int = 0,
):
    """
    Get shops that have sold at least 1 combo in history at the specified locker location.

    Args:
        location_id: ID of the locker location
        user: Optional authenticated user
        db: Database session
        limit: Number of items per page
        offset: Number of items to skip

    Returns:
        List of shops with distance information
    """
    shops, total = services.get_shops_by_location_service(
        location_id=location_id,
        user=user,
        db=db,
        limit=limit,
        offset=offset,
    )
    return ListResponse(limit=limit, offset=offset, total=total, data=shops)
