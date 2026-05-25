from typing import List, Optional

from sqlmodel import Session, col, select

from apps.favorites.models.favorites import Favorite


def get_favorite_by_user_and_shop(
    db: Session, user_id: str, shop_id: str
) -> Optional[Favorite]:
    statement = select(Favorite).where(
        (Favorite.user_id == user_id) & (Favorite.shop_id == shop_id)
    )
    return db.exec(statement).first()


def get_favorites_by_user_and_shops(
    db: Session, user_id: str, shop_ids: List[str]
) -> List[Favorite]:
    """Batch query to get all favorites for a user among specific shops."""
    if not shop_ids:
        return []

    statement = select(Favorite).where(
        (col(Favorite.user_id) == user_id) & (col(Favorite.shop_id).in_(shop_ids))
    )
    return list(db.exec(statement).all())


def create_favorite(db: Session, user_id: str, shop_id: str) -> Favorite:
    fav = Favorite(user_id=user_id, shop_id=shop_id)
    db.add(fav)
    db.commit()
    db.refresh(fav)
    return fav


def delete_favorite(db: Session, favorite: Favorite) -> None:
    db.delete(favorite)
    db.commit()
