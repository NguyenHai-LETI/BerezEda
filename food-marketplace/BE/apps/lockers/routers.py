from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File
from sqlmodel import Session

from apps.core.database import get_session
from apps.core.schemas import SuccessResponse, ListResponse
from apps.auth.permissions import AdminUser, LockerOwnerOrAdminUser, CustomerUser, AuthenticatedUser, AuthenticatedUserOrNone
from apps.lockers import crud, services
from apps.lockers.schemas import (
    LockerLocationCreate, LockerLocationUpdate, LockerLocationResponse,
    LockerUnitCreate, LockerUnitUpdate, LockerUnitResponse, FavoriteLockerResponse,
)
from apps.integrations.firebase_client import firebase_service

router = APIRouter(prefix="/lockers", tags=["Ячейки"])


def _sync_location(loc) -> None:
    firebase_service.sync_locker_location(loc.id, {
        "id": loc.id, "name": loc.name, "address": loc.address,
        "latitude": loc.latitude, "longitude": loc.longitude,
        "is_active": loc.is_active,
    })


def _sync_unit(unit) -> None:
    firebase_service.sync_locker_unit(unit.location_id, unit.id, {
        "id": unit.id, "location_id": unit.location_id,
        "unit_number": unit.unit_number, "status": unit.status,
        "size": unit.size, "is_active": unit.is_active,
        "temperature": unit.temperature,
    })


@router.post("/sync-firebase", response_model=SuccessResponse)
def sync_all_lockers_to_firebase(
    current_user: AdminUser,
    db: Session = Depends(get_session),
):
    """Sync all locker locations and their units from DB to Firebase."""
    locations = crud.get_all_locations(db, active_only=False)
    synced = 0
    for loc in locations:
        _sync_location(loc)
        units = crud.get_units_by_location(db, loc.id, active_only=False)
        for unit in units:
            _sync_unit(unit)
        synced += 1
    return SuccessResponse(
        data={"locations_synced": synced},
        message=f"Синхронизировано {synced} постаматов",
    )


@router.get("", response_model=ListResponse[LockerLocationResponse])
def list_lockers(
    user: AuthenticatedUserOrNone,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    db: Session = Depends(get_session),
):
    locations = crud.get_all_locations(db, active_only=True)
    result = []
    for loc in locations:
        units = crud.get_units_by_location(db, loc.id)
        data = LockerLocationResponse.model_validate(loc)
        data.units = units
        if lat and lon:
            data.distance_km = round(crud.calc_distance_km(lat, lon, loc.latitude, loc.longitude), 1)
        result.append(data)
    if lat and lon:
        result.sort(key=lambda x: x.distance_km or 9999)
    return ListResponse(data=result, total=len(result))


@router.get("/owner/my", response_model=ListResponse[LockerLocationResponse])
def get_my_lockers(current_user: LockerOwnerOrAdminUser, db: Session = Depends(get_session)):
    locations = crud.get_locations_by_owner(db, current_user.id)
    result = []
    for loc in locations:
        units = crud.get_units_by_location(db, loc.id, active_only=False)
        data = LockerLocationResponse.model_validate(loc)
        data.units = units
        result.append(data)
    return ListResponse(data=result, total=len(result))


@router.get("/favorites", response_model=ListResponse[FavoriteLockerResponse])
def get_favorite_lockers(current_user: CustomerUser, db: Session = Depends(get_session)):
    favs = crud.get_favorites_by_user(db, current_user.id)
    result = []
    for fav in favs:
        loc = crud.get_location_by_id(db, fav.locker_location_id)
        item = FavoriteLockerResponse.model_validate(fav)
        if loc:
            units = crud.get_units_by_location(db, loc.id)
            loc_data = LockerLocationResponse.model_validate(loc)
            loc_data.units = units
            item.locker = loc_data
        result.append(item)
    return ListResponse(data=result, total=len(result))


@router.post("/favorites", response_model=SuccessResponse, status_code=201)
def add_favorite_locker(
    locker_location_id: str,
    current_user: CustomerUser,
    db: Session = Depends(get_session),
):
    services.get_location_or_404(db, locker_location_id)
    existing = crud.get_favorite_by_user_and_locker(db, current_user.id, locker_location_id)
    if not existing:
        crud.add_favorite(db, current_user.id, locker_location_id)
    return SuccessResponse(message="Добавлено в избранное")


@router.delete("/favorites/{favorite_id}", response_model=SuccessResponse)
def remove_favorite_locker(favorite_id: str, current_user: CustomerUser, db: Session = Depends(get_session)):
    from apps.lockers.exceptions import favorite_locker_not_found
    from sqlmodel import select
    from apps.lockers.models import FavoriteLocker
    fav = db.exec(
        select(FavoriteLocker).where(FavoriteLocker.id == favorite_id, FavoriteLocker.user_id == current_user.id)
    ).first()
    if not fav:
        raise favorite_locker_not_found()
    crud.remove_favorite(db, fav)
    return SuccessResponse(message="Удалено из избранного")


@router.get("/{location_id}", response_model=SuccessResponse[LockerLocationResponse])
def get_locker(location_id: str, user: AuthenticatedUserOrNone, db: Session = Depends(get_session)):
    loc = services.get_location_or_404(db, location_id)
    units = crud.get_units_by_location(db, loc.id)
    data = LockerLocationResponse.model_validate(loc)
    data.units = units
    return SuccessResponse(data=data)


@router.get("/{location_id}/shops", response_model=ListResponse)
def get_locker_shops(location_id: str, user: AuthenticatedUserOrNone, db: Session = Depends(get_session)):
    services.get_location_or_404(db, location_id)
    from apps.shops.crud import get_all_shops
    shops = get_all_shops(db, locker_location_id=location_id)
    from apps.shops.schemas import ShopResponse
    return ListResponse(data=shops, total=len(shops))


@router.post("", response_model=SuccessResponse[LockerLocationResponse], status_code=201)
def create_locker(body: LockerLocationCreate, current_user: LockerOwnerOrAdminUser, db: Session = Depends(get_session)):
    payload = body.model_dump()
    unit_count = payload.pop("unit_count", 0)
    loc = crud.create_location(db, current_user.id, payload)
    _sync_location(loc)
    # Auto-create units if unit_count specified
    units = []
    for i in range(1, (unit_count or 0) + 1):
        unit = crud.create_unit(db, loc.id, {"unit_number": i})
        _sync_unit(unit)
        units.append(unit)
    data = LockerLocationResponse.model_validate(loc)
    data.units = [LockerUnitResponse.model_validate(u) for u in units]
    return SuccessResponse(data=data, message="Постамат создан")


@router.put("/{location_id}", response_model=SuccessResponse[LockerLocationResponse])
def update_locker(
    location_id: str,
    body: LockerLocationUpdate,
    current_user: LockerOwnerOrAdminUser,
    db: Session = Depends(get_session),
):
    from apps.lockers.exceptions import locker_access_denied
    loc = services.get_location_or_404(db, location_id)
    if current_user.role != "admin" and loc.owner_id != current_user.id:
        raise locker_access_denied()
    updated = crud.update_location(db, loc, body.model_dump(exclude_none=True))
    _sync_location(updated)
    data = LockerLocationResponse.model_validate(updated)
    data.units = [LockerUnitResponse.model_validate(u) for u in crud.get_units_by_location(db, updated.id)]
    return SuccessResponse(data=data, message="Ячейка обновлена")


@router.delete("/{location_id}", response_model=SuccessResponse)
def delete_locker(
    location_id: str,
    current_user: LockerOwnerOrAdminUser,
    db: Session = Depends(get_session),
):
    from apps.lockers.exceptions import locker_access_denied
    from sqlmodel import select
    from apps.lockers.models import LockerUnit

    loc = services.get_location_or_404(db, location_id)
    if current_user.role != "admin" and loc.owner_id != current_user.id:
        raise locker_access_denied()

    units = crud.get_units_by_location(db, location_id, active_only=False)
    occupied = [u for u in units if u.status in ("OCCUPIED", "RESERVED", "occupied", "reserved")]
    if occupied:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Невозможно удалить: {len(occupied)} ячеек используется",
        )

    # Delete all units first
    for unit in units:
        crud.delete_unit(db, unit)

    # Delete location
    db.delete(loc)
    db.commit()

    # Remove from Firebase
    try:
        fb = firebase_service.get_db()
        if fb:
            fb.collection("locker_locations").document(location_id).delete()
    except Exception:
        pass

    return SuccessResponse(data=None, message="Постамат удалён")


@router.post("/{location_id}/image", response_model=SuccessResponse[LockerLocationResponse])
async def upload_locker_image(
    location_id: str,
    current_user: LockerOwnerOrAdminUser,
    db: Session = Depends(get_session),
    file: UploadFile = File(...),
):
    loc = await services.upload_location_image(db, location_id, current_user.id, file, current_user.role == "admin")
    data = LockerLocationResponse.model_validate(loc)
    data.units = crud.get_units_by_location(db, loc.id)
    return SuccessResponse(data=data)


@router.post("/{location_id}/units", response_model=SuccessResponse[LockerUnitResponse], status_code=201)
def add_unit(
    location_id: str,
    body: LockerUnitCreate,
    current_user: LockerOwnerOrAdminUser,
    db: Session = Depends(get_session),
):
    from apps.lockers.exceptions import locker_access_denied
    loc = services.get_location_or_404(db, location_id)
    if current_user.role != "admin" and loc.owner_id != current_user.id:
        raise locker_access_denied()
    unit = crud.create_unit(db, location_id, body.model_dump())
    _sync_unit(unit)
    return SuccessResponse(data=unit, message="Бокс добавлен")


@router.put("/units/{unit_id}", response_model=SuccessResponse[LockerUnitResponse])
def update_unit(
    unit_id: str,
    body: LockerUnitUpdate,
    current_user: LockerOwnerOrAdminUser,
    db: Session = Depends(get_session),
):
    unit = services.get_unit_or_404(db, unit_id)
    updated = crud.update_unit(db, unit, body.model_dump(exclude_none=True))
    return SuccessResponse(data=updated, message="Бокс обновлён")

@router.get('/{location_id}/units', response_model=ListResponse[LockerUnitResponse])
def list_units(
    location_id: str,
    current_user: LockerOwnerOrAdminUser,
    db: Session = Depends(get_session),
):
    from apps.lockers.exceptions import locker_access_denied
    loc = services.get_location_or_404(db, location_id)
    if current_user.role != 'admin' and loc.owner_id != current_user.id:
        raise locker_access_denied()
    units = crud.get_units_by_location(db, location_id, active_only=False)
    return ListResponse(data=units, total=len(units))


@router.delete('/units/{unit_id}', response_model=SuccessResponse)
def delete_unit(
    unit_id: str,
    current_user: LockerOwnerOrAdminUser,
    db: Session = Depends(get_session),
):
    from apps.lockers.exceptions import locker_access_denied, locker_unit_occupied
    unit = services.get_unit_or_404(db, unit_id)
    loc = services.get_location_or_404(db, unit.location_id)
    if current_user.role != 'admin' and loc.owner_id != current_user.id:
        raise locker_access_denied()
    if unit.status not in ('AVAILABLE', 'MAINTENANCE', 'available', 'maintenance'):
        raise locker_unit_occupied()
    location_id = unit.location_id
    unit_id = unit.id
    crud.delete_unit(db, unit)
    # Remove from Firebase
    db2 = None
    try:
        fb = firebase_service.get_db()
        if fb:
            (fb.collection("locker_locations").document(location_id)
               .collection("units").document(unit_id).delete())
    except Exception:
        pass
    return SuccessResponse(data=None, message='Бокс удалён')


@router.post("/{location_id}/units/import-csv", response_model=SuccessResponse)
async def import_units_csv(
    location_id: str,
    current_user: LockerOwnerOrAdminUser,
    db: Session = Depends(get_session),
    file: UploadFile = File(...),
):
    """Import locker units from CSV. Columns: unit_number, size (optional), temperature (optional)
    Skips rows where unit_number already exists for this location.
    """
    import io, csv
    from apps.lockers.exceptions import locker_access_denied
    from sqlmodel import select
    from apps.lockers.models import LockerUnit

    loc = services.get_location_or_404(db, location_id)
    if current_user.role != "admin" and loc.owner_id != current_user.id:
        raise locker_access_denied()

    content = await file.read()
    text = content.decode("utf-8-sig")  # handle BOM
    reader = csv.DictReader(io.StringIO(text))

    existing_numbers = {
        u.unit_number for u in db.exec(
            select(LockerUnit).where(LockerUnit.location_id == location_id)
        ).all()
    }

    created = []
    for row in reader:
        try:
            unit_number = int(row.get("unit_number", "").strip())
        except (ValueError, AttributeError):
            continue
        if unit_number in existing_numbers:
            continue
        size = (row.get("size") or "").strip() or None
        temp_str = (row.get("temperature") or "").strip()
        temperature = float(temp_str) if temp_str else None
        unit = crud.create_unit(db, location_id, {
            "unit_number": unit_number,
            "size": size,
            "temperature": temperature,
        })
        _sync_unit(unit)
        existing_numbers.add(unit_number)
        created.append(unit)

    return SuccessResponse(
        data={"created": len(created)},
        message=f"Импортировано {len(created)} ячеек",
    )

