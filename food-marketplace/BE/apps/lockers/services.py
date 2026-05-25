from datetime import datetime
from sqlmodel import Session
from fastapi import UploadFile

from apps.lockers import crud
from apps.lockers.exceptions import (
    locker_not_found, locker_unit_not_found, locker_unit_not_available,
    locker_access_denied, favorite_locker_not_found,
)
from apps.lockers.models import LockerLocation, LockerUnit
from apps.integrations.file_storage import file_storage
from apps.integrations.firebase_client import firebase_service


def get_location_or_404(db: Session, location_id: str) -> LockerLocation:
    loc = crud.get_location_by_id(db, location_id)
    if not loc:
        raise locker_not_found()
    return loc


def get_unit_or_404(db: Session, unit_id: str) -> LockerUnit:
    unit = crud.get_unit_by_id(db, unit_id)
    if not unit:
        raise locker_unit_not_found()
    return unit


def assert_available(unit: LockerUnit):
    if unit.status not in ("AVAILABLE", "available") or not unit.is_active:
        raise locker_unit_not_available()


def mark_unit_reserved(db: Session, unit_id: str) -> LockerUnit:
    unit = get_unit_or_404(db, unit_id)
    updated = crud.update_unit(db, unit, {"status": "RESERVED"})
    _sync_unit_firebase(db, updated)
    return updated


def mark_unit_occupied(db: Session, unit_id: str) -> LockerUnit:
    unit = get_unit_or_404(db, unit_id)
    updated = crud.update_unit(db, unit, {"status": "OCCUPIED"})
    _sync_unit_firebase(db, updated)
    return updated


def mark_unit_available(db: Session, unit_id: str) -> LockerUnit:
    unit = get_unit_or_404(db, unit_id)
    updated = crud.update_unit(db, unit, {"status": "AVAILABLE"})
    _sync_unit_firebase(db, updated)
    return updated


def _sync_unit_firebase(db: Session, unit: LockerUnit):
    firebase_service.sync_locker_unit(
        unit.location_id, unit.id,
        {"id": unit.id, "unit_number": unit.unit_number, "status": unit.status,
         "temperature": unit.temperature, "size": unit.size, "is_active": unit.is_active},
    )


async def upload_location_image(db: Session, location_id: str, owner_id: str, file: UploadFile, is_admin: bool) -> LockerLocation:
    loc = get_location_or_404(db, location_id)
    if not is_admin and loc.owner_id != owner_id:
        raise locker_access_denied()
    if loc.image:
        file_storage.delete(loc.image)
    path = await file_storage.upload(file, subfolder="lockers")
    return crud.update_location(db, loc, {"image": path})
