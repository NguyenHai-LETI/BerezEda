from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File
from sqlmodel import Session

from apps.core.database import get_session
from apps.core.schemas import SuccessResponse, ListResponse
from apps.auth.permissions import ShopOwnerOrAdminUser, AuthenticatedUser, AuthenticatedUserOrNone
from apps.combos import crud, services
from apps.combos.schemas import ComboCreate, ComboUpdate, ComboAssignLocker, ComboResponse

router = APIRouter(prefix="/combos", tags=["Наборы"])


def _enrich(db: Session, combo) -> ComboResponse:
    from apps.combos.schemas import ComboProductResponse, ComboLockerInfo
    data = ComboResponse.model_validate(combo)

    # Enrich shop name
    from apps.shops.models import Shop
    shop = db.get(Shop, combo.shop_id)
    if shop:
        data.shop_name = shop.name
        data.shop_avg_rating = float(shop.avg_rating or 0)
        data.shop_total_reviews = int(shop.total_reviews or 0)

    combo_products = crud.get_combo_products(db, combo.id)

    # Enrich products with name and first image
    enriched_products = []
    for cp in combo_products:
        cp_data = ComboProductResponse.model_validate(cp)
        from apps.products.models.product import ProductMaster
        product = db.get(ProductMaster, cp.product_id)
        if product:
            cp_data.product_name = product.name
            imgs = product.images
            if isinstance(imgs, str):
                import json
                try: imgs = json.loads(imgs)
                except: imgs = []
            if imgs and isinstance(imgs, list) and len(imgs) > 0:
                cp_data.product_image = imgs[0]
        enriched_products.append(cp_data)
    data.products = enriched_products

    # Enrich locker info
    if combo.locker_location_id:
        from apps.lockers.models import LockerLocation, LockerUnit
        loc = db.get(LockerLocation, combo.locker_location_id)
        unit = db.get(LockerUnit, combo.locker_unit_id) if combo.locker_unit_id else None
        data.locker_info = ComboLockerInfo(
            locker_name=loc.name if loc else None,
            locker_address=loc.address if loc else None,
            unit_number=unit.unit_number if unit else None,
            locker_lat=loc.latitude if loc else None,
            locker_lng=loc.longitude if loc else None,
        )

    return data


@router.get("", response_model=ListResponse[ComboResponse])
def list_combos(
    user: AuthenticatedUserOrNone,
    locker_location_id: Optional[str] = None,
    shop_id: Optional[str] = None,
    db: Session = Depends(get_session),
):
    combos = crud.get_available_combos(db, locker_location_id=locker_location_id, shop_id=shop_id)
    return ListResponse(data=[_enrich(db, c) for c in combos], total=len(combos))


@router.get("/my", response_model=ListResponse[ComboResponse])
def get_my_combos(
    status: Optional[str] = None,
    current_user: ShopOwnerOrAdminUser = ...,
    db: Session = Depends(get_session),
):
    from apps.shops.crud import get_shop_by_owner
    shop = get_shop_by_owner(db, current_user.id)
    if not shop:
        return ListResponse(data=[], total=0)
    combos = crud.get_combos_by_shop(db, shop.id, status=status)
    return ListResponse(data=[_enrich(db, c) for c in combos], total=len(combos))


@router.get("/{combo_id}", response_model=SuccessResponse[ComboResponse])
def get_combo(combo_id: str, user: AuthenticatedUserOrNone, db: Session = Depends(get_session)):
    combo = services.get_combo_or_404(db, combo_id)
    return SuccessResponse(data=_enrich(db, combo))


@router.post("", response_model=SuccessResponse[ComboResponse], status_code=201)
def create_combo(body: ComboCreate, current_user: ShopOwnerOrAdminUser, db: Session = Depends(get_session)):
    from apps.shops.crud import get_shop_by_owner
    from apps.shops.exceptions import shop_not_found
    shop = get_shop_by_owner(db, current_user.id)
    if not shop:
        raise shop_not_found()
    data = body.model_dump()
    data["products"] = [p.model_dump() for p in body.products]
    combo = services.create_combo(db, shop.id, data)
    return SuccessResponse(data=_enrich(db, combo), message="Набор создан как черновик")


@router.put("/{combo_id}", response_model=SuccessResponse[ComboResponse])
def update_combo(
    combo_id: str,
    body: ComboUpdate,
    current_user: ShopOwnerOrAdminUser,
    db: Session = Depends(get_session),
):
    from apps.shops.crud import get_shop_by_owner
    from apps.combos.exceptions import combo_not_draft
    shop = get_shop_by_owner(db, current_user.id)
    combo = services.get_combo_or_404(db, combo_id)
    services.assert_shop_owner(combo, shop.id if shop else "")
    if combo.status != "draft":
        raise combo_not_draft()
    updated = crud.update_combo(db, combo, body.model_dump(exclude_none=True))
    return SuccessResponse(data=_enrich(db, updated), message="Набор обновлён")


@router.put("/{combo_id}/assign-locker", response_model=SuccessResponse[ComboResponse])
def assign_locker(
    combo_id: str,
    body: ComboAssignLocker,
    current_user: ShopOwnerOrAdminUser,
    db: Session = Depends(get_session),
):
    """Step 3-4: choose locker unit → system generates access code. Status → ready."""
    from apps.shops.crud import get_shop_by_owner
    shop = get_shop_by_owner(db, current_user.id)
    combo = services.assign_locker(
        db, combo_id,
        shop.id if shop else "",
        body.locker_unit_id,
        body.locker_location_id,
    )
    return SuccessResponse(data=_enrich(db, combo), message="Постамат выбран, код доступа сгенерирован")


@router.put("/{combo_id}/confirm-placed", response_model=SuccessResponse[ComboResponse])
def confirm_placed(combo_id: str, current_user: ShopOwnerOrAdminUser, db: Session = Depends(get_session)):
    """Step 5: seller simulates placing item → SELLING."""
    from apps.shops.crud import get_shop_by_owner
    shop = get_shop_by_owner(db, current_user.id)
    combo = services.confirm_placed(db, combo_id, shop.id if shop else "")
    return SuccessResponse(data=_enrich(db, combo), message="Набор выставлен на продажу")


@router.post("/{combo_id}/image", response_model=SuccessResponse[ComboResponse])
async def upload_combo_image(
    combo_id: str,
    current_user: ShopOwnerOrAdminUser,
    db: Session = Depends(get_session),
    file: UploadFile = File(...),
):
    from apps.shops.crud import get_shop_by_owner
    from apps.integrations.file_storage import file_storage
    shop = get_shop_by_owner(db, current_user.id)
    combo = services.get_combo_or_404(db, combo_id)
    services.assert_shop_owner(combo, shop.id if shop else "")
    path = await file_storage.upload(file, subfolder="combos")
    updated = crud.update_combo(db, combo, {"image": path})
    return SuccessResponse(data=_enrich(db, updated), message="Изображение загружено")


@router.put("/{combo_id}/cancel", response_model=SuccessResponse[ComboResponse])
def cancel_combo(combo_id: str, current_user: ShopOwnerOrAdminUser, db: Session = Depends(get_session)):
    from apps.shops.crud import get_shop_by_owner
    shop = get_shop_by_owner(db, current_user.id)
    combo = services.cancel_combo(db, combo_id, shop.id if shop else "")
    return SuccessResponse(data=combo, message="Набор отменён")
