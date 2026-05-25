from typing import Optional, List
from sqlmodel import Session, select

from apps.core.utils import utcnow

from apps.shops.models import Shop, ShopLockerAssociation


def get_shop_by_id(db: Session, shop_id: str) -> Optional[Shop]:
    return db.get(Shop, shop_id)


# Alias used by many modules
def get_shop(db: Session, shop_id: str) -> Optional[Shop]:
    return db.get(Shop, shop_id)


def get_shop_by_code(db: Session, code: str) -> Optional[Shop]:
    return db.exec(select(Shop).where(Shop.code == code)).first()


def get_shop_by_owner(db: Session, owner_id: str) -> Optional[Shop]:
    return db.exec(select(Shop).where(Shop.owner_id == owner_id)).first()


def get_all_shops(
    db: Session,
    locker_location_id: Optional[str] = None,
    search: Optional[str] = None,
) -> List[Shop]:
    q = select(Shop).where(Shop.is_active == True)
    if locker_location_id:
        assoc_ids = db.exec(
            select(ShopLockerAssociation.shop_id).where(
                ShopLockerAssociation.locker_location_id == locker_location_id,
                ShopLockerAssociation.is_active == True,
            )
        ).all()
        q = q.where(Shop.id.in_(assoc_ids))
    if search:
        q = q.where(Shop.name.ilike(f"%{search}%"))
    return db.exec(q).all()


def create_shop(db: Session, owner_id: str, data: dict) -> Shop:
    shop = Shop(owner_id=owner_id, **data)
    db.add(shop)
    db.commit()
    db.refresh(shop)
    return shop


def update_shop(db: Session, shop: Shop, data: dict) -> Shop:
    for k, v in data.items():
        setattr(shop, k, v)
    shop.updated_at = utcnow()
    db.add(shop)
    db.commit()
    db.refresh(shop)
    return shop


def associate_locker(db: Session, shop_id: str, locker_location_id: str) -> ShopLockerAssociation:
    existing = db.exec(
        select(ShopLockerAssociation).where(
            ShopLockerAssociation.shop_id == shop_id,
            ShopLockerAssociation.locker_location_id == locker_location_id,
        )
    ).first()
    if existing:
        existing.is_active = True
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing
    assoc = ShopLockerAssociation(shop_id=shop_id, locker_location_id=locker_location_id)
    db.add(assoc)
    db.commit()
    db.refresh(assoc)
    return assoc


def get_locker_ids_for_shop(db: Session, shop_id: str) -> List[str]:
    return db.exec(
        select(ShopLockerAssociation.locker_location_id).where(
            ShopLockerAssociation.shop_id == shop_id,
            ShopLockerAssociation.is_active == True,
        )
    ).all()


def get_shop_with_users(db: Session, shop_id: str) -> Optional[Shop]:
    """Load shop with owner and staff_members pre-fetched for notification dispatch."""
    shop = db.get(Shop, shop_id)
    if shop:
        # Touch relationships while session is open so get_all_shop_users() works
        _ = shop.owner
        _ = list(shop.staff_members)
    return shop


def get_all_active_shops(db: Session) -> List[Shop]:
    return db.exec(select(Shop).where(Shop.is_active == True)).all()
