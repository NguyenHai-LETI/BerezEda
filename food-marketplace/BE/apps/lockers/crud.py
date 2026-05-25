import math
from typing import Optional, List
from sqlmodel import Session, select

from apps.core.utils import utcnow

from apps.lockers.models import LockerLocation, LockerUnit, FavoriteLocker


def get_location_by_id(db: Session, location_id: str) -> Optional[LockerLocation]:
    return db.get(LockerLocation, location_id)


# Aliases used by validators
def get_locker_location_by_id(db: Session, location_id: str) -> Optional[LockerLocation]:
    return db.get(LockerLocation, location_id)


def get_locker_location_by_code(db: Session, code: str) -> Optional[LockerLocation]:
    return db.exec(select(LockerLocation).where(LockerLocation.code == code)).first()


def get_locker_unit_by_id(db: Session, unit_id: str) -> Optional[LockerUnit]:
    return db.get(LockerUnit, unit_id)


def get_all_locations(db: Session, active_only: bool = True) -> List[LockerLocation]:
    q = select(LockerLocation)
    if active_only:
        q = q.where(LockerLocation.is_active == True)
    return db.exec(q).all()


def get_locations_by_owner(db: Session, owner_id: str) -> List[LockerLocation]:
    return db.exec(select(LockerLocation).where(LockerLocation.owner_id == owner_id)).all()


def create_location(db: Session, owner_id: str, data: dict) -> LockerLocation:
    loc = LockerLocation(owner_id=owner_id, **data)
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc


def update_location(db: Session, loc: LockerLocation, data: dict) -> LockerLocation:
    for k, v in data.items():
        setattr(loc, k, v)
    loc.updated_at = utcnow()
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc


def get_units_by_location(db: Session, location_id: str, active_only: bool = True) -> List[LockerUnit]:
    q = select(LockerUnit).where(LockerUnit.location_id == location_id)
    if active_only:
        q = q.where(LockerUnit.is_active == True)
    return db.exec(q.order_by(LockerUnit.unit_number)).all()


def get_unit_by_id(db: Session, unit_id: str) -> Optional[LockerUnit]:
    return db.get(LockerUnit, unit_id)


def create_unit(db: Session, location_id: str, data: dict) -> LockerUnit:
    if not data.get("unit_number"):
        existing = db.exec(
            select(LockerUnit).where(LockerUnit.location_id == location_id)
        ).all()
        data["unit_number"] = max((u.unit_number for u in existing), default=0) + 1
    unit = LockerUnit(location_id=location_id, **data)
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit


def update_unit(db: Session, unit: LockerUnit, data: dict) -> LockerUnit:
    for k, v in data.items():
        setattr(unit, k, v)
    unit.updated_at = utcnow()
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit



def delete_unit(db: Session, unit: LockerUnit) -> None:
    db.delete(unit)
    db.commit()

def get_favorite_by_user_and_locker(db: Session, user_id: str, locker_location_id: str) -> Optional[FavoriteLocker]:
    return db.exec(
        select(FavoriteLocker).where(
            FavoriteLocker.user_id == user_id,
            FavoriteLocker.locker_location_id == locker_location_id,
        )
    ).first()


def get_favorites_by_user(db: Session, user_id: str) -> List[FavoriteLocker]:
    return db.exec(select(FavoriteLocker).where(FavoriteLocker.user_id == user_id)).all()


def add_favorite(db: Session, user_id: str, locker_location_id: str) -> FavoriteLocker:
    fav = FavoriteLocker(user_id=user_id, locker_location_id=locker_location_id)
    db.add(fav)
    db.commit()
    db.refresh(fav)
    return fav


def remove_favorite(db: Session, fav: FavoriteLocker) -> None:
    db.delete(fav)
    db.commit()


def calc_distance_km(lat1, lon1, lat2, lon2) -> float:
    if None in (lat1, lon1, lat2, lon2):
        return 0.0
    R = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = math.sin(d_lat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
