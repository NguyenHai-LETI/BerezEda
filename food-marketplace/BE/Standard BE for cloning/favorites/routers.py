from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer
from sqlmodel import Session

from apps.auth.permissions import CustomerUser
from apps.core.database import get_session
from apps.core.schemas import ListResponse, SuccessResponse
from apps.shops.schemas import ShopReadWithDistance

from . import schemas, services

router = APIRouter(tags=["Favorites"])
security = HTTPBearer()


@router.get("/favorites", response_model=ListResponse[ShopReadWithDistance])
def list_favorites(
    user: CustomerUser,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_session),
    user_lat: Optional[str] = None,
    user_lng: Optional[str] = None,
):
    shops, total = services.get_liked_shop_service(
        db, user, limit, offset, user_location=f"{user_lat},{user_lng}"
    )
    return ListResponse(limit=limit, offset=offset, total=total, data=shops)


@router.post("/favorites", response_model=SuccessResponse)
def toggle_favorite(
    user: CustomerUser,
    body: schemas.FavoriteCreate,
    db: Session = Depends(get_session),
):
    result = services.like_or_dislike_service(db, user, body.is_like, body.shop_id)
    return SuccessResponse(message=f"Favorite {result['action']} successfully")
