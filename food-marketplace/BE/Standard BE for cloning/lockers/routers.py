from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlmodel import Session

from apps.auth.permissions import (
    AdminUser,
    AuthenticatedUser,
    AuthenticatedUserOrNone,
    CustomerUser,
    ShopLockerOwnerOrAdminUser,
    ShopOwnerOrAdminUser,
)
from apps.core.database import get_session
from apps.core.schemas import ListResponse, SuccessResponse
from apps.integrations.galilei import galilei_service
from apps.lockers.schemas import (
    AvailableUnitResponse,
    CheckAvailabilityRequest,
    CollectItemRequest,
    FavoriteLockerCreate,
    FavoriteLockerRead,
    FavoriteLockerReorder,
    LockerLocationCreate,
    LockerLocationPublicRead,
    LockerLocationRead,
    LockerLocationUpdate,
    LockerLocationWithUnits,
    LockerReservationCreate,
    LockerReservationRead,
    LockerReservationUpdate,
    LockerUnitCreate,
    LockerUnitImportResponse,
    LockerUnitRead,
    LockerUnitSetTemperatureByColumn,
    ReservationTimingInfo,
    SearchHistoryCreate,
    SearchHistoryRead,
    ShopCooldownInfo,
    SyncFromGuestResponse,
)
from apps.lockers.services import (
    add_favorite_locker_service,
    add_search_history_service,
    cancel_locker_reservation_service,
    check_availability_service,
    check_shop_cooldown_service,
    collect_item_service,
    create_locker_location_service,
    create_locker_reservation_service,
    create_locker_unit_service,
    get_locker_location_service,
    get_locker_reservation_service,
    get_locker_status_service,
    get_locker_unit_service,
    get_reservation_timing_info,
    list_favorite_lockers_service,
    list_locker_locations_service,
    list_locker_units_service,
    list_public_locker_locations_service,
    list_search_history_service,
    remove_favorite_locker_service,
    reorder_favorite_lockers_service,
    sync_from_guest_service,
    update_locker_location_service,
    set_temperature_by_column_service,
    update_locker_reservation_service,
)

router = APIRouter(tags=["Lockers"])


# ===== Galilei Integration Endpoints =====
@router.get("/{locker_id}/status", response_model=SuccessResponse[dict])
def get_locker_unit_status(full_unit_number: str):
    """Get Galilei locker status"""
    # Use default locker_id from service if not provided
    if full_unit_number is None or not galilei_service.is_configured():
        raise HTTPException(status_code=500, detail="Galilei service not configured")

    data = get_locker_status_service(full_unit_number)
    return SuccessResponse(data=data)


# ===== LockerLocation Endpoints =====
@router.get("/locations/public", response_model=ListResponse[LockerLocationPublicRead])
def list_public_locker_locations(
    user: AuthenticatedUserOrNone,
    db: Session = Depends(get_session),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_lat: Optional[str] = Query(None),
    user_lng: Optional[str] = Query(None),
    is_selling_combo: Optional[bool] = Query(None),
    search: Optional[str] = Query(None, description="Partial match on locker name or address"),
):
    """Get active locker locations that have at least one registered shop"""
    locations, total = list_public_locker_locations_service(
        db,
        limit=limit,
        offset=offset,
        user_lat=user_lat,
        user_lng=user_lng,
        user_id=user.id if user else None,
        is_selling_combo=is_selling_combo,
        search=search,
    )
    return ListResponse(data=locations, total=total, limit=limit, offset=offset)


# ===== Favorite Lockers (My Locker) Endpoints =====


@router.get("/favorites", response_model=ListResponse[FavoriteLockerRead])
def list_favorite_lockers(
    user: CustomerUser,
    db: Session = Depends(get_session),
    user_lat: Optional[str] = Query(None),
    user_lng: Optional[str] = Query(None),
):
    """List current user's favorite locker locations (max 3), ordered by priority."""
    data = list_favorite_lockers_service(
        db, user.id, user_lat=user_lat, user_lng=user_lng
    )
    return ListResponse(data=data, total=len(data), limit=len(data), offset=0)


@router.post("/favorites", response_model=SuccessResponse[dict])
def add_favorite_locker(
    user: CustomerUser,
    body: FavoriteLockerCreate,
    db: Session = Depends(get_session),
):
    """Add a locker location to favorites (max 3)."""
    add_favorite_locker_service(db, user.id, body.locker_location_id)
    return SuccessResponse(data=None)


@router.delete("/favorites/{location_id}", response_model=SuccessResponse[dict])
def remove_favorite_locker(
    user: CustomerUser,
    location_id: str,
    db: Session = Depends(get_session),
):
    """Remove a locker location from favorites."""
    remove_favorite_locker_service(db, user.id, location_id)
    return SuccessResponse(data=None)


@router.patch("/favorites/reorder", response_model=SuccessResponse[dict])
def reorder_favorite_lockers(
    user: CustomerUser,
    body: FavoriteLockerReorder,
    db: Session = Depends(get_session),
):
    """Update the priority order of favorite lockers (order in list = priority 1, 2, 3)."""
    reorder_favorite_lockers_service(db, user.id, body.locker_location_ids)
    return SuccessResponse(data=None)


@router.post(
    "/favorites/sync-from-guest",
    response_model=SuccessResponse[SyncFromGuestResponse],
)
def sync_favorites_from_guest(
    user: CustomerUser,
    body: FavoriteLockerReorder,
    db: Session = Depends(get_session),
):
    """Sync guest's local favorite list to user account (only if user has no favorites)."""
    result = sync_from_guest_service(db, user.id, body.locker_location_ids)
    return SuccessResponse(data=result, message="Sync completed")


@router.get("/locations", response_model=ListResponse[LockerLocationRead])
def list_locker_locations(
    user: ShopLockerOwnerOrAdminUser,
    owner_id: Optional[str] = None,
    db: Session = Depends(get_session),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List locker locations"""
    locations, total = list_locker_locations_service(
        db, owner_id=owner_id, user=user, limit=limit, offset=offset
    )
    return ListResponse(data=locations, total=total, limit=limit, offset=offset)


@router.get("/locations/my-locations", response_model=ListResponse[LockerLocationRead])
def list_my_locker_locations(
    user: ShopLockerOwnerOrAdminUser,
    db: Session = Depends(get_session),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List all locker locations owned by the current user"""
    locations, total = list_locker_locations_service(
        db, owner_id=user.id, user=user, limit=limit, offset=offset
    )
    return ListResponse(data=locations, total=total, limit=limit, offset=offset)


@router.get(
    "/locations/owner/{owner_id}", response_model=ListResponse[LockerLocationRead]
)
def list_locker_locations_by_owner(
    owner_id: str,
    user: AdminUser,
    db: Session = Depends(get_session),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    locations, total = list_locker_locations_service(
        db, owner_id=owner_id, user=user, limit=limit, offset=offset
    )
    return ListResponse(data=locations, total=total, limit=limit, offset=offset)


@router.get(
    "/locations/{location_id}", response_model=SuccessResponse[LockerLocationWithUnits]
)
def get_locker_location(
    location_id: str,
    user: AuthenticatedUserOrNone = None,
    db: Session = Depends(get_session),
    user_lat: Optional[str] = None,
    user_lng: Optional[str] = None,
):
    """Get locker location details by ID with all units"""
    location = get_locker_location_service(
        location_id, db, user_lat=user_lat, user_lng=user_lng
    )
    return SuccessResponse(data=location)


# ===== LockerUnit Temperature Endpoints =====
@router.patch(
    "/locations/{location_id}/temperatures/by-column",
    response_model=SuccessResponse[List[LockerUnitRead]],
)
def set_temperature_by_column(
    location_id: str,
    body: LockerUnitSetTemperatureByColumn,
    user: ShopLockerOwnerOrAdminUser,
    db: Session = Depends(get_session),
):
    """Set temperature for all locker units in a specific physical column of a location"""
    units = set_temperature_by_column_service(location_id, body.column_index, body.temperature, user, db)
    return SuccessResponse(data=units)


@router.post(
    "/locations",
    response_model=SuccessResponse[LockerLocationRead],
    status_code=status.HTTP_201_CREATED,
)
def create_locker_location(
    location: LockerLocationCreate,
    user: ShopLockerOwnerOrAdminUser,
    db: Session = Depends(get_session),
):
    """Create a new locker location"""
    created_location = create_locker_location_service(location, user, db)
    return SuccessResponse(data=created_location)


@router.put(
    "/locations/{location_id}",
    response_model=SuccessResponse[LockerLocationRead],
)
def update_locker_location(
    location_id: str,
    update_data: LockerLocationUpdate,
    user: ShopLockerOwnerOrAdminUser,
    db: Session = Depends(get_session),
):
    """Update an existing locker location"""
    updated_location = update_locker_location_service(
        location_id, update_data, user, db
    )
    return SuccessResponse(data=updated_location)


# ===== LockerUnit Endpoints =====
@router.get("/units", response_model=SuccessResponse[List[LockerUnitRead]])
def list_locker_units(
    user: AuthenticatedUser,
    location_id: Optional[str] = Query(None, description="Filter by location ID"),
    status: Optional[str] = Query(None, description="Filter by unit status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_session),
):
    """List locker units"""
    units, total = list_locker_units_service(
        db,
        location_id=location_id,
        status=status,
        limit=limit,
        offset=offset,
    )

    return ListResponse(data=units, total=total, limit=limit, offset=offset)


@router.get("/units/{unit_id}", response_model=SuccessResponse[LockerUnitRead])
def get_locker_unit(
    user: AuthenticatedUser,
    unit_id: str,
    db: Session = Depends(get_session),
):
    """Get locker unit by ID"""
    unit = get_locker_unit_service(unit_id, user, db)
    return SuccessResponse(data=unit)


@router.post(
    "/units",
    response_model=SuccessResponse[LockerUnitRead],
    status_code=status.HTTP_201_CREATED,
)
def create_locker_unit(
    user: ShopOwnerOrAdminUser,
    unit: LockerUnitCreate,
    db: Session = Depends(get_session),
):
    """Create a new locker unit"""
    created_unit = create_locker_unit_service(unit, user, db)
    return SuccessResponse(data=created_unit)


# ===== LockerReservation Endpoints =====
@router.get(
    "/reservations/{reservation_id}",
    response_model=SuccessResponse[LockerReservationRead],
)
def get_locker_reservation(
    user: AuthenticatedUser,
    reservation_id: str,
    db: Session = Depends(get_session),
):
    """Get locker reservation by ID"""
    reservation = get_locker_reservation_service(reservation_id, user, db)
    return SuccessResponse(data=reservation)


@router.post(
    "/reservations",
    response_model=SuccessResponse[LockerReservationRead],
    status_code=status.HTTP_201_CREATED,
)
def create_locker_reservation(
    user: AuthenticatedUser,
    reservation: LockerReservationCreate,
    db: Session = Depends(get_session),
):
    """Create a new locker reservation"""
    created_reservation = create_locker_reservation_service(reservation, user, db)
    return SuccessResponse(data=created_reservation)


@router.patch(
    "/reservations/{reservation_id}",
    response_model=SuccessResponse[LockerReservationRead],
)
def update_locker_reservation(
    user: AuthenticatedUser,
    reservation_id: str,
    reservation: LockerReservationUpdate,
    db: Session = Depends(get_session),
):
    """Update locker reservation"""
    updated_reservation = update_locker_reservation_service(
        reservation_id, reservation, user, db
    )
    return SuccessResponse(data=updated_reservation)


@router.delete("/reservations/{reservation_id}", response_model=SuccessResponse[dict])
def cancel_locker_reservation(
    user: AuthenticatedUser,
    reservation_id: str,
    db: Session = Depends(get_session),
):
    """Cancel locker reservation"""
    result = cancel_locker_reservation_service(reservation_id, user, db)
    return SuccessResponse(data=result)


# ===== Special Action Endpoints =====
@router.post(
    "/availability", response_model=SuccessResponse[list[AvailableUnitResponse]]
)
def check_locker_availability(
    request: CheckAvailabilityRequest,
    db: Session = Depends(get_session),
):
    """Check availability of locker units for a specific time period"""
    available_units = check_availability_service(request, db)
    return SuccessResponse(data=available_units)


@router.post(
    "/reservations/collect", response_model=SuccessResponse[LockerReservationRead]
)
def collect_item(
    user: AuthenticatedUser,
    request: CollectItemRequest,
    db: Session = Depends(get_session),
):
    """Mark item as collected from locker"""
    updated_reservation = collect_item_service(request, user, db)
    return SuccessResponse(data=updated_reservation)


@router.get(
    "/reservations/{reservation_id}/timing",
    response_model=SuccessResponse[ReservationTimingInfo],
)
def get_reservation_timing(
    reservation_id: str,
    user: AuthenticatedUser,
    db: Session = Depends(get_session),
):
    """Get timing information for a reservation including countdown and status"""
    timing_info = get_reservation_timing_info(reservation_id, db)
    return SuccessResponse(data=timing_info)


@router.get(
    "/shops/{shop_id}/cooldown", response_model=SuccessResponse[ShopCooldownInfo]
)
def check_shop_cooldown(
    shop_id: str,
    user: AuthenticatedUser,
    db: Session = Depends(get_session),
):
    """Check if a shop is in cooldown period after failed combo placement"""
    cooldown_info = check_shop_cooldown_service(shop_id, db)
    return SuccessResponse(data=cooldown_info)


@router.get("/shops/my/cooldown", response_model=SuccessResponse[ShopCooldownInfo])
def check_my_shop_cooldown(
    user: AuthenticatedUser,
    db: Session = Depends(get_session),
):
    """Check if the current shop is in cooldown period"""
    associated_shop = user.get_associated_shop()
    shop_id = associated_shop.id if associated_shop else user.id
    cooldown_info = check_shop_cooldown_service(str(shop_id), db)
    return SuccessResponse(data=cooldown_info)


@router.post(
    "/units/import-csv", response_model=SuccessResponse[LockerUnitImportResponse]
)
def import_locker_units_csv(
    user: ShopLockerOwnerOrAdminUser,
    db: Session = Depends(get_session),
    location_id: str = Form(
        ..., description="Location ID to assign the locker units to"
    ),
    csv_file: UploadFile = File(
        ..., description="CSV file containing locker unit data"
    ),
):
    """
    Import locker units from CSV file.

    Expected CSV format:
    - Column 4 (locker_ID): Will be used as unit_number
    - All other columns are ignored

    Only admin users can import locker units.
    """
    from .import_csv import import_locker_units_from_csv

    # Validate file type
    if not csv_file.filename or not csv_file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File must be a CSV file"
        )

    try:
        # Read CSV content
        csv_content = csv_file.file.read().decode("utf-8")

        # Import units
        result = import_locker_units_from_csv(db, location_id, csv_content)

        if not result.success and result.imported_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Import failed: {'; '.join(result.errors[:3])}",  # Show first 3 errors
            )

        return SuccessResponse(data=result)

    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid CSV file encoding. Please use UTF-8.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during import: {str(e)}",
        )


# ===== Search History Endpoints =====
@router.post("/search-history", response_model=SuccessResponse[dict], status_code=201)
def add_search_history(
    user: CustomerUser,
    body: SearchHistoryCreate,
    db: Session = Depends(get_session),
):
    """Add or update a locker location in user's search history (max 5 unique locations)."""
    add_search_history_service(db, user.id, body.locker_location_id)
    return SuccessResponse(data=None)


@router.get("/search-history", response_model=ListResponse[SearchHistoryRead])
def list_search_history(
    user: CustomerUser,
    db: Session = Depends(get_session),
):
    """Get user's search history sorted by searched_at desc (max 5 items)."""
    data = list_search_history_service(db, user.id)
    return ListResponse(data=data, total=len(data), limit=len(data), offset=0)
