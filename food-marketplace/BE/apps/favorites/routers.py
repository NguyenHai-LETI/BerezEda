from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from pydantic import BaseModel

from apps.core.database import get_session
from apps.core.schemas import SuccessResponse, ListResponse
from apps.auth.permissions import CustomerUser
from apps.favorites import crud

router = APIRouter(prefix="/favorites", tags=["Избранное"])


class FavoriteShopRequest(BaseModel):
    shop_id: str


@router.get("/shops", response_model=ListResponse)
def get_favorite_shops(current_user: CustomerUser, db: Session = Depends(get_session)):
    favs = crud.get_favorites_by_user(db, current_user.id)
    shop_ids = [f.shop_id for f in favs]
    from apps.shops.crud import get_shop_by_id
    shops = [get_shop_by_id(db, sid) for sid in shop_ids]
    shops = [s for s in shops if s]
    return ListResponse(data=shops, total=len(shops))


@router.post("/shops", response_model=SuccessResponse, status_code=201)
def add_favorite_shop(body: FavoriteShopRequest, current_user: CustomerUser, db: Session = Depends(get_session)):
    from apps.shops.services import get_shop_or_404
    get_shop_or_404(db, body.shop_id)
    if not crud.get_favorite(db, current_user.id, body.shop_id):
        crud.add_favorite(db, current_user.id, body.shop_id)
    return SuccessResponse(message="Добавлено в избранное")


@router.delete("/shops/{shop_id}", response_model=SuccessResponse)
def remove_favorite_shop(shop_id: str, current_user: CustomerUser, db: Session = Depends(get_session)):
    fav = crud.get_favorite(db, current_user.id, shop_id)
    if not fav:
        raise HTTPException(status_code=404, detail="Магазин не в избранном")
    crud.remove_favorite(db, fav)
    return SuccessResponse(message="Удалено из избранного")
