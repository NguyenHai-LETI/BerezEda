from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File
from sqlmodel import Session

from apps.core.database import get_session
from apps.core.schemas import SuccessResponse, ListResponse
from apps.auth.permissions import ShopOwnerOrAdminUser, AuthenticatedUser, AuthenticatedUserOrNone, LockerOwnerOrAdminUser
from apps.shops import crud, services
from apps.shops.schemas import ShopCreate, ShopUpdate, ShopResponse, ShopAssociateLockerRequest

router = APIRouter(prefix="/shops", tags=["Магазины"])


@router.get("", response_model=ListResponse[ShopResponse])
def list_shops(
    user: AuthenticatedUserOrNone,
    locker_location_id: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_session),
):
    shops = crud.get_all_shops(db, locker_location_id=locker_location_id, search=search)
    return ListResponse(data=shops, total=len(shops))


@router.get("/my", response_model=SuccessResponse[ShopResponse])
def get_my_shop(current_user: ShopOwnerOrAdminUser, db: Session = Depends(get_session)):
    from apps.shops.exceptions import shop_not_found
    shop = crud.get_shop_by_owner(db, current_user.id)
    if not shop:
        raise shop_not_found()
    return SuccessResponse(data=shop)


@router.get("/{shop_id}", response_model=SuccessResponse[ShopResponse])
def get_shop(shop_id: str, user: AuthenticatedUserOrNone, db: Session = Depends(get_session)):
    shop = services.get_shop_or_404(db, shop_id)
    return SuccessResponse(data=shop)


@router.post("", response_model=SuccessResponse[ShopResponse], status_code=201)
def create_shop(body: ShopCreate, current_user: ShopOwnerOrAdminUser, db: Session = Depends(get_session)):
    shop = services.create_shop_for_owner(db, current_user.id, body.model_dump())
    return SuccessResponse(data=shop, message="Магазин успешно создан")


@router.put("/{shop_id}", response_model=SuccessResponse[ShopResponse])
def update_shop(shop_id: str, body: ShopUpdate, current_user: ShopOwnerOrAdminUser, db: Session = Depends(get_session)):
    shop = services.update_shop_by_owner(
        db, shop_id, current_user.id,
        body.model_dump(exclude_none=True),
        is_admin=(current_user.role == "admin"),
    )
    return SuccessResponse(data=shop, message="Магазин обновлён")


@router.post("/{shop_id}/image", response_model=SuccessResponse[ShopResponse])
async def upload_image(
    shop_id: str,
    current_user: ShopOwnerOrAdminUser,
    db: Session = Depends(get_session),
    file: UploadFile = File(...),
):
    shop = await services.upload_shop_image(db, shop_id, current_user.id, file)
    return SuccessResponse(data=shop, message="Изображение загружено")


@router.post("/{shop_id}/lockers", response_model=SuccessResponse)
def associate_locker(
    shop_id: str,
    body: ShopAssociateLockerRequest,
    current_user: AuthenticatedUser,
    db: Session = Depends(get_session),
):
    from apps.shops.exceptions import shop_access_denied
    from fastapi import HTTPException
    shop = services.get_shop_or_404(db, shop_id)
    if current_user.role == "admin":
        pass  # admin can always associate
    elif current_user.role == "owner_locker":
        # Locker owner must own the locker being associated
        from apps.lockers.crud import get_location_by_id
        loc = get_location_by_id(db, body.locker_location_id)
        if not loc or loc.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Нет доступа к этому постамату")
    elif current_user.role == "owner_shop":
        # Shop owner must own the shop
        if shop.owner_id != current_user.id:
            raise shop_access_denied()
    else:
        raise HTTPException(status_code=403, detail="Доступ запрещён")
    crud.associate_locker(db, shop_id, body.locker_location_id)
    return SuccessResponse(message="Магазин привязан к ячейке")


@router.get("/my/lockers", response_model=ListResponse)
def get_my_shop_lockers(current_user: ShopOwnerOrAdminUser, db: Session = Depends(get_session)):
    from apps.shops.crud import get_shop_by_owner, get_locker_ids_for_shop
    from apps.lockers.crud import get_location_by_id, get_units_by_location
    from apps.lockers.schemas import LockerLocationResponse

    shop = get_shop_by_owner(db, current_user.id)
    if not shop:
        return ListResponse(data=[], total=0)
    locker_ids = get_locker_ids_for_shop(db, shop.id)
    result = []
    for lid in locker_ids:
        loc = get_location_by_id(db, lid)
        if loc:
            units = get_units_by_location(db, lid, active_only=False)
            data = LockerLocationResponse.model_validate(loc)
            data.units = units
            result.append(data)
    return ListResponse(data=result, total=len(result))
