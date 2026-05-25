from typing import List, Optional
from sqlmodel import Session, select
from apps.favorites.models import Favorite


def get_favorites_by_user(db: Session, user_id: str) -> List[Favorite]:
    return db.exec(select(Favorite).where(Favorite.user_id == user_id)).all()


def get_favorite(db: Session, user_id: str, shop_id: str) -> Optional[Favorite]:
    return db.exec(
        select(Favorite).where(Favorite.user_id == user_id, Favorite.shop_id == shop_id)
    ).first()


def add_favorite(db: Session, user_id: str, shop_id: str) -> Favorite:
    fav = Favorite(user_id=user_id, shop_id=shop_id)
    db.add(fav)
    db.commit()
    db.refresh(fav)
    return fav


def remove_favorite(db: Session, fav: Favorite) -> None:
    db.delete(fav)
    db.commit()


# Aliases used by services
def get_favorite_by_user_and_shop(db: Session, user_id: str, shop_id: str) -> Optional[Favorite]:
    return get_favorite(db, user_id, shop_id)


def create_favorite(db: Session, user_id: str, shop_id: str) -> Favorite:
    return add_favorite(db, user_id, shop_id)


def delete_favorite(db: Session, fav: Favorite) -> None:
    return remove_favorite(db, fav)


def get_user_ids_following_shop(db: Session, shop_id: str) -> List[str]:
    return db.exec(select(Favorite.user_id).where(Favorite.shop_id == shop_id)).all()


def get_user_ids_following_locker(db: Session, locker_location_id: str) -> List[str]:
    from apps.lockers.models import FavoriteLocker
    return db.exec(
        select(FavoriteLocker.user_id).where(FavoriteLocker.locker_location_id == locker_location_id)
    ).all()
