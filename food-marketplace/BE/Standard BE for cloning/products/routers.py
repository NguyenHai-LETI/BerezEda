from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from apps.auth.permissions import (
    AdminUser,
    AuthenticatedUserOrNone,
    ShopOwnerOrAdminUser,
)
from apps.core.database import get_session
from apps.core.schemas import ListResponse, SuccessResponse

from . import schemas, services

combos_router = APIRouter(tags=["Combos"])
product_master_router = APIRouter(tags=["ProductMasters"])


@combos_router.get("/", response_model=ListResponse[schemas.ComboListRead])
def list_combos(
    user: ShopOwnerOrAdminUser,
    db: Session = Depends(get_session),
    limit: int = 20,
    offset: int = 0,
    is_draft: Optional[bool] = None,  # Filter by draft status
):
    combos, total = services.list_combos_service(
        db, user=user, limit=limit, offset=offset, is_draft=is_draft
    )
    return ListResponse(limit=limit, offset=offset, total=total, data=combos)


@combos_router.get("/public", response_model=ListResponse[schemas.ComboListRead])
def list_public_combos(
    user: AuthenticatedUserOrNone,
    db: Session = Depends(get_session),
    limit: int = 20,
    offset: int = 0,
    shop_id: Optional[str] = None,  # Filter by shop
    category: Optional[str] = None,  # Filter by category
    user_lat: Optional[str] = None,
    user_lng: Optional[str] = None,
    distance: Optional[float] = Query(None),
):
    """Get publicly available combos for customers to purchase"""
    combos, total = services.list_public_combos_service(
        db,
        user=user,
        limit=limit,
        offset=offset,
        shop_id=shop_id,
        category=category,
        user_lat=user_lat,
        user_lng=user_lng,
        distance=distance,
    )
    return ListResponse(limit=limit, offset=offset, total=total, data=combos)


@combos_router.get(
    "/location/{location_id}", response_model=ListResponse[schemas.ComboListRead]
)
def list_combos_by_locker_location(
    location_id: str,
    user: AuthenticatedUserOrNone,
    db: Session = Depends(get_session),
    limit: int = 20,
    offset: int = 0,
    category: Optional[str] = None,
    is_selling: Optional[bool] = Query(
        default=None, description="Filter combos by selling status"
    ),
):
    """Get all combos available in a specific locker location"""
    combos, total = services.list_combos_by_locker_location_service(
        db,
        location_id=location_id,
        user=user,
        limit=limit,
        offset=offset,
        category=category,
        is_selling=is_selling,
    )
    return ListResponse(limit=limit, offset=offset, total=total, data=combos)


@combos_router.post("/", response_model=SuccessResponse[schemas.ComboRead])
def create_combo(
    user: ShopOwnerOrAdminUser,
    combo: schemas.ComboCreate,
    db: Session = Depends(get_session),
):
    combo_obj = services.create_combo_service(combo, user, db)
    return SuccessResponse(data=combo_obj)


@combos_router.post("/draft", response_model=SuccessResponse[schemas.ComboRead])
def save_combo_draft(
    user: ShopOwnerOrAdminUser,
    combo: schemas.ComboDraftCreate,
    db: Session = Depends(get_session),
):
    """Save combo as draft without strict validation - allows incomplete data"""
    combo_obj = services.save_combo_draft_service(combo, user, db)
    return SuccessResponse(data=combo_obj)


@combos_router.post("/preview", response_model=SuccessResponse[schemas.ComboPreview])
def preview_combo(
    user: ShopOwnerOrAdminUser,
    combo: schemas.ComboCreate,
    db: Session = Depends(get_session),
):
    """Preview combo creation with calculated prices and product details"""
    combo_preview = services.preview_combo_service(combo, user, db)
    return SuccessResponse(data=combo_preview)


@combos_router.get(
    "/{combo_id}", response_model=SuccessResponse[schemas.ComboFlattenedRead]
)
def get_combo(
    user: AuthenticatedUserOrNone,
    combo_id: str,
    db: Session = Depends(get_session),
):
    combo_obj = services.get_combo_service(combo_id, user, db)
    return SuccessResponse(data=combo_obj)


@combos_router.put(
    "/{combo_id}", response_model=SuccessResponse[schemas.ComboFlattenedRead]
)
def update_combo(
    user: ShopOwnerOrAdminUser,
    combo_id: str,
    update: schemas.ComboUpdate,
    db: Session = Depends(get_session),
):
    combo_obj = services.update_combo_service(combo_id, update, user, db)
    return SuccessResponse(data=combo_obj)


@combos_router.put(
    "/edit/{combo_id}", response_model=SuccessResponse[schemas.ComboFlattenedRead]
)
def edit_combo(
    user: ShopOwnerOrAdminUser,
    combo_id: str,
    update: schemas.ComboEdit,
    db: Session = Depends(get_session),
):
    """
    Edit selling combo information.
    Allows editing specific combo-related information:
    - listing_end_date (sales time)
    - images (product images)
    - name (product name)
    - description (product description)
    - is_free (donation mode setting) + discount_percentage
    - products: Optional[List[ComboProductCreate]] = None
    - sales_duration
    """
    combo_obj = services.edit_combo_service(combo_id, update, user, db)
    return SuccessResponse(data=combo_obj)


@combos_router.post("/cancel/{combo_id}", response_model=SuccessResponse)
def cancel_combo(
    user: ShopOwnerOrAdminUser,
    combo_id: str,
    db: Session = Depends(get_session),
):
    """
    Cancel a selling combo.

    - If combo status is SOLD, raises an error (cannot cancel sold combos)
    - If combo status is SELLING:
      - Changes combo status to DELETED
      - Sets combo is_available to False
      - Updates combo updated_at time
      - Changes locker_reservation status to COMPLETED
      - Changes locker_unit status to AVAILABLE
    - Returns empty data (None) after successful cancellation
    """
    services.cancel_selling_combo_service(combo_id, user, db)
    return SuccessResponse(data=None)


@combos_router.delete("/{combo_id}", response_model=SuccessResponse)
def delete_combo(
    user: ShopOwnerOrAdminUser,
    combo_id: str,
    is_draft: bool = Query(False),
    db: Session = Depends(get_session),
):
    services.delete_combo_service(combo_id, user, db, is_draft=is_draft)
    return SuccessResponse(data=None)


@combos_router.post("/cleanup/expired", response_model=SuccessResponse)
def cleanup_expired_combos(
    user: AdminUser,
    db: Session = Depends(get_session),
):
    """
    Manually trigger cleanup of expired combos and their associated locker units.
    Only accessible by admin users.

    This endpoint:
    1. Finds combos that have expired (listing_end_date < current_time)
    2. Updates their status to 'expired'
    3. Sets associated locker units to 'available'
    4. Triggers Firebase sync for updated locations
    """
    result = services.cleanup_expired_combos_and_lockers_service(db)
    return SuccessResponse(data=result)


@combos_router.post("/cleanup/combo/{combo_id}", response_model=SuccessResponse)
def cleanup_single_combo(
    combo_id: str,
    user: ShopOwnerOrAdminUser,
    db: Session = Depends(get_session),
):
    """
    Manually clean up locker units for a specific expired combo.
    Accessible by shop owners (for their own combos) and admin users.
    """
    result = services.cleanup_single_combo_locker_units_service(db, combo_id)
    return SuccessResponse(data=result)


@combos_router.post("/cleanup/schedule", response_model=SuccessResponse)
def schedule_cleanup_task(
    user: AdminUser,
    db: Session = Depends(get_session),
):
    """
    Schedule a background cleanup task for expired combos.
    Only accessible by admin users.
    """
    from apps.products.tasks import cleanup_expired_combos_and_lockers_task

    task = cleanup_expired_combos_and_lockers_task.delay()
    return SuccessResponse(
        data={
            "task_id": task.id,
            "status": "scheduled",
            "message": "Cleanup task has been scheduled to run in the background",
        }
    )


# -------- PRODUCT MASTER ENDPOINT ---------------------------------
@product_master_router.get("/", response_model=ListResponse[schemas.ProductMasterRead])
def list_product_masters(
    user: ShopOwnerOrAdminUser,
    db: Session = Depends(get_session),
    name: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
):
    product_masters, total = services.list_product_masters_service(
        db, user=user, name=name, limit=limit, offset=offset
    )
    return ListResponse(limit=limit, offset=offset, total=total, data=product_masters)


@product_master_router.post(
    "/", response_model=SuccessResponse[schemas.ProductMasterRead]
)
def create_product_master(
    user: ShopOwnerOrAdminUser,
    product_master: schemas.ProductMasterCreate,
    db: Session = Depends(get_session),
):
    product_obj = services.create_product_master_service(product_master, user, db)
    return SuccessResponse(data=product_obj)


@product_master_router.get(
    "/{product_master_id}",
    response_model=SuccessResponse[schemas.ProductMasterRead],
)
def get_product_master(
    user: ShopOwnerOrAdminUser,
    product_master_id: str,
    db: Session = Depends(get_session),
):
    product_obj = services.get_product_master_service(product_master_id, user, db)
    return SuccessResponse(data=product_obj)


@product_master_router.put(
    "/{product_master_id}",
    response_model=SuccessResponse[schemas.ProductMasterRead],
)
def update_product_master(
    user: ShopOwnerOrAdminUser,
    product_master_id: str,
    update: schemas.ProductMasterUpdate,
    db: Session = Depends(get_session),
):
    product_obj = services.update_product_master_service(
        product_master_id, update, user, db
    )
    return SuccessResponse(data=product_obj)


@product_master_router.delete("/{product_master_id}", response_model=SuccessResponse)
def delete_product_master(
    user: ShopOwnerOrAdminUser,
    product_master_id: str,
    db: Session = Depends(get_session),
):
    services.delete_product_master_service(product_master_id, user, db)
    return SuccessResponse(data=None)
