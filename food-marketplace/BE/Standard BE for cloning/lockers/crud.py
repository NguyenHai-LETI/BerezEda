from typing import List, Optional
from datetime import datetime, timezone

from sqlmodel import Session, and_, select

from apps.core.constants import (
    RESERVATION_STATUS_ACTIVE,
    RESERVATION_STATUS_CANCELLED,
    RESERVATION_STATUS_PENDING,
    UNIT_STATUS_AVAILABLE,
)
from apps.core.utils import get_current_time

from .models.favorite_locker import FavoriteLocker
from .models.location import LockerLocation
from .models.reservation import LockerReservation
from .models.search_history import LockerSearchHistory
from .models.shop_cooldown import ShopCooldown
from .models.unit import LockerUnit


# ===== LockerLocation CRUD =====
def get_locker_location_by_id(
    db: Session, location_id: str
) -> Optional[LockerLocation]:
    """Get locker location by ID"""
    return db.get(LockerLocation, location_id)


def get_locker_location_by_code(db: Session, code: str) -> Optional[LockerLocation]:
    """Get locker location by code"""
    statement = select(LockerLocation).where(LockerLocation.code == code)
    return db.exec(statement).first()


def get_locker_locations(
    db: Session,
    shop_id: Optional[str] = None,
    owner_id: Optional[str] = None,
    is_active: Optional[bool] = None,
    user=None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[List[LockerLocation], int]:
    """Get locker locations with optional filtering by shop_id, owner_id, or user role"""
    statement = select(LockerLocation)

    # Filter by owner_id if provided
    if owner_id:
        statement = statement.where(LockerLocation.owner_id == owner_id)

    # Filter by shop_id if provided (through association table)
    if shop_id:
        from .models.shop_locker_association import ShopLockerAssociation

        statement = statement.join(ShopLockerAssociation).where(
            ShopLockerAssociation.shop_id == shop_id
        )

    # Filter by active status
    if is_active is not None:
        statement = statement.where(LockerLocation.is_active == is_active)

    if user and user.role == "owner_shop":
        associated_shop = user.get_associated_shop()
        if associated_shop:
            from .models.shop_locker_association import ShopLockerAssociation

            statement = statement.join(ShopLockerAssociation).where(
                ShopLockerAssociation.shop_id == associated_shop.id
            )

    # Get total count
    total_statement = statement
    total = len(db.exec(total_statement).all())

    # Apply pagination
    paginated_statement = statement.offset(offset).limit(limit)
    locations = db.exec(paginated_statement).all()

    return list(locations), total


def get_public_locker_locations(
    db: Session,
    search: Optional[str] = None,
) -> List[LockerLocation]:
    """Get active locker locations that have at least one registered shop"""
    from .models.shop_locker_association import ShopLockerAssociation

    # Query locations that are active AND have at least one shop association
    statement = (
        select(LockerLocation)
        .join(ShopLockerAssociation)
        .where(LockerLocation.is_active == True)
        .distinct()
    )

    if search:
        search_pattern = f"%{search}%"
        statement = statement.where(
            LockerLocation.name.ilike(search_pattern)
            | LockerLocation.address.ilike(search_pattern)
        )

    locations = db.exec(statement).all()
    return list(locations)


def create_locker_location(db: Session, location: LockerLocation) -> LockerLocation:
    """Create a new locker location"""
    db.add(location)
    db.commit()
    db.refresh(location)
    return location


def delete_locker_location(db: Session, location_id: str) -> bool:
    """Delete locker location (soft delete by setting is_active=False)"""
    location = db.get(LockerLocation, location_id)
    if location:
        location.is_active = False
        location.updated_at = get_current_time()
        db.commit()
        return True
    return False


def get_pending_reservation_by_shop(
    db: Session, shop_id: str
) -> Optional[LockerReservation]:
    """Get pending reservation for a shop"""
    statement = select(LockerReservation).where(
        LockerReservation.shop_id == shop_id,
        LockerReservation.status == RESERVATION_STATUS_PENDING,
    )
    return db.exec(statement).first()


def get_pending_reservation_by_user(
    db: Session, user_id: str
) -> Optional[LockerReservation]:
    """Get pending reservation for a user"""
    statement = select(LockerReservation).where(
        LockerReservation.user_id == user_id,
        LockerReservation.status == RESERVATION_STATUS_PENDING,
    )
    return db.exec(statement).first()


# ===== LockerUnit CRUD =====
def get_locker_unit_by_id(db: Session, unit_id: str) -> Optional[LockerUnit]:
    """Get locker unit by ID"""
    return db.get(LockerUnit, unit_id)


def get_locker_units(
    db: Session,
    location_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[List[LockerUnit], int]:
    """Get locker units with optional filtering"""
    statement = select(LockerUnit)

    # Filter by location
    if location_id:
        statement = statement.where(LockerUnit.location_id == location_id)

    # Filter by status
    if status:
        statement = statement.where(LockerUnit.status == status)

    # Get total count
    total_statement = statement
    total = len(db.exec(total_statement).all())

    # Apply pagination
    paginated_statement = statement.offset(offset).limit(limit)
    units = db.exec(paginated_statement).all()

    return list(units), total


def get_locker_units_by_list_locations(
    db: Session, location_ids: list
) -> list[LockerUnit]:
    stmt = select(LockerUnit).where(LockerUnit.location_id.in_(location_ids))
    locker_units = db.execute(stmt).scalars().all()
    return locker_units


def get_available_units_immediate(
    db: Session,
    location_id: str,
    size: Optional[str] = None,
) -> List[LockerUnit]:
    """Get immediately available locker units for real-time booking"""
    # Base query for available units
    statement = select(LockerUnit).where(
        and_(
            LockerUnit.location_id == location_id,
            LockerUnit.status == UNIT_STATUS_AVAILABLE,
            LockerUnit.is_active == True,
        )
    )

    # Filter by size if provided
    if size:
        statement = statement.where(LockerUnit.size == size)

    return list(db.exec(statement).all())


def create_locker_unit(db: Session, unit: LockerUnit) -> LockerUnit:
    """Create a new locker unit"""
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit


def update_locker_unit(
    db: Session, unit_id: str, unit_data: dict
) -> Optional[LockerUnit]:
    """Update locker unit"""
    unit = db.get(LockerUnit, unit_id)
    if unit:
        for key, value in unit_data.items():
            if hasattr(unit, key):
                setattr(unit, key, value)
        unit.updated_at = get_current_time()
        db.commit()
        db.refresh(unit)
    return unit


def delete_locker_unit(db: Session, unit_id: str) -> bool:
    """Delete locker unit (soft delete by setting is_active=False)"""
    unit = db.get(LockerUnit, unit_id)
    if unit:
        unit.is_active = False
        unit.updated_at = get_current_time()
        db.commit()
        return True
    return False


# ===== LockerReservation CRUD =====
def get_locker_reservation_by_id(
    db: Session, reservation_id: str
) -> Optional[LockerReservation]:
    """Get locker reservation by ID"""
    return db.get(LockerReservation, reservation_id)


def get_locker_reservations_by_combo_id(
    db: Session, combo_id: str
) -> Optional[LockerReservation]:
    """Get all locker reservations by combo ID"""
    statement = select(LockerReservation).where(LockerReservation.combo_id == combo_id)
    return db.exec(statement).first()


def get_access_codes_by_locker_units_and_combo_status(
    db: Session,
    unit_ids: List[str],
    combo_status: Optional[str] = None,
) -> List[str]:
    """Get access codes from reservations belonging to the given locker unit IDs.
    Optionally filter by the associated combo's status."""
    from apps.products.models.combos import Combo

    statement = (
        select(LockerReservation.access_code)
        .join(Combo, LockerReservation.combo_id == Combo.id)
        .where(LockerReservation.locker_unit_id.in_(unit_ids))
        .where(LockerReservation.access_code.is_not(None))
    )
    if combo_status:
        statement = statement.where(Combo.status == combo_status)
    return db.exec(statement).all()


def get_locker_reservation_by_unit_and_shop(
    db: Session, unit_id: str, shop_id: str
) -> Optional[LockerReservation]:
    """Get active locker reservation by unit and shop"""

    statement = select(LockerReservation).where(
        LockerReservation.locker_unit_id == unit_id,
        LockerReservation.shop_id == shop_id,
        LockerReservation.status == RESERVATION_STATUS_PENDING,
    )
    return db.exec(statement).first()


def create_locker_reservation(
    db: Session, reservation: LockerReservation
) -> LockerReservation:
    """Create a new locker reservation"""
    db.add(reservation)
    db.commit()
    db.refresh(reservation)
    return reservation


def update_locker_reservation(
    db: Session, reservation_id: str, reservation_data: dict
) -> Optional[LockerReservation]:
    """Update locker reservation"""
    reservation = db.get(LockerReservation, reservation_id)
    if reservation:
        for key, value in reservation_data.items():
            if hasattr(reservation, key):
                setattr(reservation, key, value)
        reservation.updated_at = get_current_time()
        db.commit()
        db.refresh(reservation)
    return reservation


def cancel_locker_reservation(db: Session, reservation_id: str) -> bool:
    """Cancel locker reservation"""
    reservation = db.get(LockerReservation, reservation_id)
    if reservation and reservation.status in [
        RESERVATION_STATUS_PENDING,
        RESERVATION_STATUS_ACTIVE,
    ]:
        reservation.status = RESERVATION_STATUS_CANCELLED
        reservation.updated_at = get_current_time()
        db.commit()
        return True
    return False


# ===== ShopCooldown CRUD =====
def create_shop_cooldown(db: Session, cooldown: ShopCooldown) -> ShopCooldown:
    """Create a new shop cooldown record"""
    db.add(cooldown)
    db.commit()
    db.refresh(cooldown)
    return cooldown


def get_active_shop_cooldown(db: Session, shop_id: str) -> Optional[ShopCooldown]:
    """Get active cooldown for a shop"""
    get_current_time()
    statement = select(ShopCooldown).where(
        and_(
            ShopCooldown.shop_id == shop_id,
            ShopCooldown.is_active == True,
            ShopCooldown.cooldown_end > get_current_time(),
        )
    )
    return db.exec(statement).first()


def deactivate_shop_cooldown(db: Session, shop_id: str) -> None:
    """Deactivate all cooldowns for a shop (when they successfully place a combo)"""
    statement = select(ShopCooldown).where(
        and_(ShopCooldown.shop_id == shop_id, ShopCooldown.is_active == True)
    )
    cooldowns = db.exec(statement).all()
    for cooldown in cooldowns:
        cooldown.is_active = False
    db.commit()


# ===== FavoriteLocker CRUD =====


def get_favorite_locker_by_user_and_location(
    db: Session, user_id: str, locker_location_id: str
) -> Optional[FavoriteLocker]:
    """Get favorite locker by user and location."""
    statement = select(FavoriteLocker).where(
        FavoriteLocker.user_id == user_id,
        FavoriteLocker.locker_location_id == locker_location_id,
    )
    return db.exec(statement).first()


def get_favorite_lockers_by_user_and_locations(
    db: Session, user_id: str, location_ids: List[str]
) -> List[FavoriteLocker]:
    """Batch query favorite lockers for a user among specific location IDs."""
    statement = select(FavoriteLocker).where(
        FavoriteLocker.user_id == user_id,
        FavoriteLocker.locker_location_id.in_(location_ids),
    )
    return list(db.exec(statement).all())


def list_favorite_lockers_by_user(db: Session, user_id: str) -> List[FavoriteLocker]:
    """List user's favorite lockers ordered by sort_order ASC."""
    statement = (
        select(FavoriteLocker)
        .where(FavoriteLocker.user_id == user_id)
        .order_by(FavoriteLocker.sort_order.asc())
    )
    return list(db.exec(statement).all())


def count_favorite_lockers_by_user(db: Session, user_id: str) -> int:
    """Count favorite lockers for a user."""
    statement = select(FavoriteLocker).where(FavoriteLocker.user_id == user_id)
    return len(db.exec(statement).all())


def create_favorite_locker(
    db: Session,
    user_id: str,
    locker_location_id: str,
    sort_order: int,
) -> FavoriteLocker:
    """Create a favorite locker record."""
    fav = FavoriteLocker(
        user_id=user_id,
        locker_location_id=locker_location_id,
        sort_order=sort_order,
    )
    db.add(fav)
    db.commit()
    db.refresh(fav)
    return fav


def delete_favorite_locker(db: Session, favorite: FavoriteLocker) -> None:
    """Delete a favorite locker record and compact sort_order for the user."""
    user_id = favorite.user_id
    db.delete(favorite)
    db.commit()
    _compact_favorite_locker_sort_order(db, user_id)


def _compact_favorite_locker_sort_order(db: Session, user_id: str) -> None:
    """Reassign sort_order to 1, 2, 3... for remaining favorites of the user."""
    favorites = list_favorite_lockers_by_user(db, user_id)
    for i, fav in enumerate(favorites, start=1):
        if fav.sort_order != i:
            fav.sort_order = i
    db.commit()


def delete_all_favorite_lockers_by_user(db: Session, user_id: str) -> None:
    """Delete all favorite locker records for a user."""
    statement = select(FavoriteLocker).where(FavoriteLocker.user_id == user_id)
    favorites = db.exec(statement).all()
    for fav in favorites:
        db.delete(fav)
    db.commit()


def update_favorite_locker_last_used_at(db: Session, favorite: FavoriteLocker) -> None:
    """Update last_used_at to current UTC time for the given favorite locker."""
    favorite.last_used_at = get_current_time()
    db.commit()


def update_sort_order_for_user(
    db: Session, user_id: str, ordered_location_ids: List[str]
) -> None:
    """Update sort_order for user's favorites to match the given order (1, 2, 3...)."""
    if not ordered_location_ids:
        return
    for sort_order, location_id in enumerate(ordered_location_ids, start=1):
        fav = get_favorite_locker_by_user_and_location(db, user_id, location_id)
        if fav and fav.sort_order != sort_order:
            fav.sort_order = sort_order
    db.commit()


# ===== LockerSearchHistory CRUD =====

def get_search_history_by_user_and_location(
    db: Session, user_id: str, locker_location_id: str
) -> Optional[LockerSearchHistory]:
    """Get search history record for a specific user and location."""
    statement = select(LockerSearchHistory).where(
        LockerSearchHistory.user_id == user_id,
        LockerSearchHistory.locker_location_id == locker_location_id,
    )
    return db.exec(statement).first()


def list_search_history_by_user(db: Session, user_id: str) -> List[LockerSearchHistory]:
    """List user's search history ordered by searched_at DESC."""
    statement = (
        select(LockerSearchHistory)
        .where(LockerSearchHistory.user_id == user_id)
        .order_by(LockerSearchHistory.searched_at.desc())
    )
    return list(db.exec(statement).all())


def count_search_history_by_user(db: Session, user_id: str) -> int:
    """Count search history records for a user."""
    statement = select(LockerSearchHistory).where(LockerSearchHistory.user_id == user_id)
    return len(db.exec(statement).all())


def get_oldest_search_history_by_user(db: Session, user_id: str) -> Optional[LockerSearchHistory]:
    """Get the oldest search history record for a user."""
    statement = (
        select(LockerSearchHistory)
        .where(LockerSearchHistory.user_id == user_id)
        .order_by(LockerSearchHistory.searched_at.asc())
        .limit(1)
    )
    return db.exec(statement).first()


def create_search_history(
    db: Session, user_id: str, locker_location_id: str
) -> LockerSearchHistory:
    """Create a new search history record."""
    import uuid
    record = LockerSearchHistory(
        id=str(uuid.uuid4()),
        user_id=user_id,
        locker_location_id=locker_location_id,
        searched_at=datetime.now(timezone.utc),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def update_search_history_searched_at(
    db: Session, record: LockerSearchHistory
) -> LockerSearchHistory:
    """Update searched_at to now for an existing search history record."""
    record.searched_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(record)
    return record


def delete_search_history(db: Session, record: LockerSearchHistory) -> None:
    """Delete a search history record."""
    db.delete(record)
    db.commit()
