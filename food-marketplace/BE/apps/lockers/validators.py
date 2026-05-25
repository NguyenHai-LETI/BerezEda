from typing import Optional

from fastapi import HTTPException
from sqlmodel import Session

from apps.auth.permissions import can_manage_shop_products
from apps.core.constants import RESERVATION_STATUS_ACTIVE, UNIT_STATUS_AVAILABLE
from apps.shops.crud import get_shop
from apps.shops.exceptions import shop_not_found

from .crud import (
    get_locker_location_by_code,
    get_locker_location_by_id,
    get_locker_unit_by_id,
)
from .exceptions import (
    access_code_invalid,
    locker_location_not_found,
    locker_unit_not_available,
    locker_unit_not_found,
    reservation_not_active,
    shop_management_required,
    unauthorized_shop_access,
)


# ===== Location Validators =====
def validate_location_creation(location_data, user, db: Session):
    """Validate location creation request"""
    # Check if shops exist and user has permission for each shop
    if location_data.shop_ids:
        for shop_id in location_data.shop_ids:
            shop = get_shop(db, shop_id)
            if not shop:
                raise shop_not_found()

    # Check if code is unique
    existing_location = get_locker_location_by_code(db, location_data.code)
    if existing_location:
        raise HTTPException(status_code=400, detail="Location code already exists")


def validate_unit_creation(unit_data, user, db: Session):
    """Validate unit creation request"""
    # Check if location exists
    location = get_locker_location_by_id(db, unit_data.location_id)
    if not location:
        raise locker_location_not_found()

    # Check permissions - user must have permission for at least one associated shop
    if location.shops:
        has_permission = False
        for shop in location.shops:
            if can_manage_shop_products(user, shop.id, db):
                has_permission = True
                break

        if not has_permission:
            raise shop_management_required()

    return location


def validate_unit_access(unit_id: str, user, db: Session):
    """Validate user has access to unit"""
    unit = get_locker_unit_by_id(db, unit_id)
    if not unit:
        raise locker_unit_not_found()

    # Check permissions - user must have permission for at least one associated shop
    location = get_locker_location_by_id(db, unit.location_id)
    if location and location.shops:
        has_permission = False
        for shop in location.shops:
            if can_manage_shop_products(user, shop.id, db):
                has_permission = True
                break

        if not has_permission:
            raise shop_management_required()

    return unit, location


# ===== Reservation Validators =====


def validate_unit_availability_immediate(unit_id: str, db: Session):
    """Validate unit exists and is immediately available for real-time booking"""
    # Check if unit exists and is available
    unit = get_locker_unit_by_id(db, unit_id)
    if not unit:
        raise locker_unit_not_found()

    if unit.status != UNIT_STATUS_AVAILABLE:
        raise locker_unit_not_available()

    # # Check if unit has any active reservations
    # active_reservation = db.exec(
    #     select(LockerReservation).where(
    #         LockerReservation.locker_unit_id == unit_id,
    #         LockerReservation.status == RESERVATION_STATUS_ACTIVE,
    #     )
    # ).first()

    # if active_reservation:
    #     raise locker_unit_already_occupied()

    return unit


def validate_reservation_access(reservation, user):
    """Validate user has access to reservation"""
    # Check access permissions
    if user.role == "customer" and reservation.user_id != user.id:
        raise unauthorized_shop_access()
    elif user.role == "owner_shop":
        associated_shop = user.get_associated_shop()
        if associated_shop and reservation.shop_id != associated_shop.id:
            raise unauthorized_shop_access()


def validate_access_code(reservation, access_code: str):
    """Validate access code matches reservation"""
    if reservation.access_code != access_code:
        raise access_code_invalid()


def validate_deposit_action(reservation):
    """Validate reservation is ready for item deposit"""
    if reservation.status != RESERVATION_STATUS_ACTIVE:
        raise reservation_not_active()


def validate_collect_action(reservation):
    """Validate reservation is ready for item collection"""
    if (
        reservation.status != RESERVATION_STATUS_ACTIVE
        or not reservation.item_deposited_at
    ):
        raise reservation_not_active()


# ===== Combo Validators =====
def validate_combo_availability(combo_id: Optional[str], db: Session):
    """Validate combo exists and is available (if provided)"""
    if combo_id:
        # TODO: Add combo validation logic when combo model is available
        # combo = get_combo_by_id(db, combo_id)
        # if not combo:
        #     raise combo_not_found()
        # if not combo.is_active:
        #     raise combo_not_available()
        pass
    return True


def validate_shop_cooldown(shop_id: str, db: Session):
    """Validate shop is not in cooldown period"""
    from apps.lockers.crud import get_active_shop_cooldown
    from apps.lockers.timing import get_cooldown_remaining_time

    active_cooldown = get_active_shop_cooldown(db, str(shop_id))
    if active_cooldown:
        cooldown_info = get_cooldown_remaining_time(active_cooldown.cooldown_end)
        if cooldown_info["in_cooldown"]:
            remaining_time = cooldown_info.get("remaining_time", "Unknown")
            raise HTTPException(
                status_code=429,  # Too Many Requests
                detail=f"Shop is in cooldown period after failed combo placement. Remaining time: {remaining_time}",
            )
