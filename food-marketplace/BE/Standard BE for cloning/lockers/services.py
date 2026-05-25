import os
import random
import time
from datetime import timedelta
from typing import List, Optional

import requests
from sqlmodel import Session, func, select

from apps.auth.permissions import can_manage_locker
from apps.core.constants import (
    COMBO_PREPARATION_TIME_MINUTES,
    COMBO_STATUS_PREPARATION_TO_LOCKER,
    COMBO_STATUS_SELLING,
    MAX_ACCESS_CODE_RETRIES,
    MAX_FAVORITE_LOCKERS,
    MAX_SEARCH_HISTORY_LOCKERS,
    ORDER_STATUS_READY_FOR_PICKUP,
    RESERVATION_STATUS_COMPLETED,
    RESERVATION_STATUS_PENDING,
    UNIT_STATUS_AVAILABLE,
    UNIT_STATUS_RESERVED,
)
from apps.core.logging import logger
from apps.core.utils import get_current_time, get_distance, parse_position_string
from apps.integrations.galilei import galilei_service
from apps.lockers.crud import get_public_locker_locations
from apps.products.models.combos import Combo

from .crud import (
    cancel_locker_reservation,
    count_favorite_lockers_by_user,
    count_search_history_by_user,
    create_favorite_locker,
    create_locker_location,
    create_locker_reservation,
    create_locker_unit,
    create_search_history,
    delete_favorite_locker,
    delete_locker_unit,
    delete_search_history,
    get_access_codes_by_locker_units_and_combo_status,
    get_available_units_immediate,
    get_favorite_locker_by_user_and_location,
    get_favorite_lockers_by_user_and_locations,
    get_locker_location_by_id,
    get_locker_locations,
    get_locker_reservation_by_id,
    get_locker_unit_by_id,
    get_locker_units,
    get_oldest_search_history_by_user,
    get_search_history_by_user_and_location,
    list_favorite_lockers_by_user,
    list_search_history_by_user,
    update_locker_reservation,
    update_locker_unit,
    update_search_history_searched_at,
    update_sort_order_for_user,
)
from .exceptions import (
    changing_locker_unit_id_not_allowed,
    column_index_out_of_range,
    favorite_locker_limit_reached,
    favorite_locker_not_found,
    favorite_locker_reorder_invalid,
    insufficient_permissions,
    locker_location_not_found,
    locker_reservation_not_found,
    locker_unit_not_found,
    locker_unit_topic_name_missing,
    locker_units_not_found_for_column,
    owner_locker_id_required,
    reservation_expired,
    temperature_not_numeric,
    temperature_out_of_range,
)
from .models.location import LockerLocation
from .models.reservation import LockerReservation
from .models.unit import LockerUnit
from .schemas import (
    AvailableUnitResponse,
    CheckAvailabilityRequest,
    CollectItemRequest,
    FavoriteLockerRead,
    LockerLocationCreate,
    LockerLocationPublicRead,
    LockerLocationUpdate,
    LockerReservationCreate,
    LockerReservationUpdate,
    LockerUnitCreate,
    LockerUnitRead,
    LockerUnitUpdate,
    SearchHistoryRead,
    SyncFromGuestResponse,
)
from .tasks import sync_location_to_firebase_task
from .utils import (
    build_locker_location_response,
    build_locker_location_with_units_response,
    calculate_locker_price,
    create_reservation_read_with_qr_code,
    generate_access_code_in,
    generate_access_code_out,
    generate_access_reset_code,
    generate_location_code,
    handle_combo_activation,
    update_unit_status_from_reservation,
)
from .validators import (
    validate_access_code,
    validate_collect_action,
    validate_location_creation,
    validate_reservation_access,
    validate_shop_cooldown,
    validate_unit_access,
    validate_unit_availability_immediate,
    validate_unit_creation,
)

# ===== Galilei Locker Integration Services =====


# ===== Galilei Locker Integration Services =====
def authenticate_locker_user():
    """
    Authenticate with Cognito and return the response containing id_token.
    """
    if not galilei_service.is_configured():
        raise Exception("Galilei service is not properly configured")

    payload = galilei_service.auth_json
    headers = {
        "Content-Type": "application/x-amz-json-1.1",
        "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
    }
    response = requests.post(
        galilei_service.get_auth_url(), json=payload, headers=headers
    )
    response.raise_for_status()
    return response.json()


def get_locker_status_service(
    full_unit_number: str,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
):
    """
    Get locker status using the locker_id and id_token (from authenticate_locker_user) as Authorization header.
    """
    # Use current datetime for the API call
    if not from_date or not to_date:
        now = get_current_time()
        from_date = now.strftime("%Y%m%d%H%M%S")
        to_date = now.strftime("%Y%m%d%H%M%S")

    url = galilei_service.get_locker_detail_url(full_unit_number, from_date, to_date)
    auth_response = authenticate_locker_user()
    id_token = auth_response["AuthenticationResult"]["IdToken"]
    headers = {"Authorization": f"Bearer {id_token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def _remove_galilei_code(locker_unit: Optional[LockerUnit], put_in: bool):
    if os.getenv("GALILEI_MODE") == "0":
        if put_in:
            access_code = "AA"
        else:
            access_code = "BB"
        url = galilei_service.get_changes_access_code_url()
        door_no = str(locker_unit.unit_number)
        topic_name = str(locker_unit.topic_name) if locker_unit.topic_name else None
        if not topic_name or topic_name == "None":
            raise locker_unit_topic_name_missing()

        data = {
            "topic_name": topic_name,
            "pin_No": access_code,
            "door_No": door_no if door_no else "1",
        }

        logger.info(f"Calling Galilei API to remove code - URL: {url}, Data: {data}")

        auth_response = authenticate_locker_user()
        id_token = auth_response["AuthenticationResult"]["IdToken"]
        headers = {"Authorization": f"Bearer {id_token}"}
        response = requests.post(url, json=data, headers=headers, timeout=10)
        response.raise_for_status()

        logger.info(
            f"Galilei API response status: {response.status_code}, Response: {response.text}"
        )

    return


def verify_galilei_door_activity(
    locker_unit: LockerUnit,
    access_code: str,
    from_date: str,
    to_date: str,
    put_in: bool = True,
) -> tuple[bool, Optional["datetime"]]:
    """
    Query Galilei Cloud to check whether a specific door was opened/closed
    with the given access code within a time range.

    Args:
        locker_unit: The locker unit to check.
        access_code: The numeric part of the code (e.g. "986725", without AA/BB prefix).
        from_date: Start of time range in JST format YYYYMMDDHHMMSS.
        to_date: End of time range in JST format YYYYMMDDHHMMSS.
        put_in: True = check shop put-in (AA, status "1"),
                False = check user take-out (BB, status "2").

    Returns:
        (found, event_datetime_utc):
            found = True if a matching record was found.
            event_datetime_utc = UTC datetime of the event, or None.
    """
    from datetime import datetime

    if os.getenv("GALILEI_MODE") != "0":
        return False, None

    expected_status = "1" if put_in else "2"

    try:
        logger.info(
            f"Querying Galilei door activity - unit: {locker_unit.full_unit_number}, "
            f"put_in: {put_in}, from: {from_date}, to: {to_date}"
        )
        records = get_locker_status_service(
            full_unit_number=locker_unit.full_unit_number,
            from_date=from_date,
            to_date=to_date,
        )

        if not records:
            logger.warning(
                f"Galilei returned empty response for unit {locker_unit.full_unit_number}"
            )
            return False, None

        unit_number = locker_unit.unit_number
        if not unit_number.startswith("0"):
            unit_number = "0" + unit_number

        logger.info(
            f"Galilei returned {len(records)} records, "
            f"expected status={expected_status}, room_No={unit_number}, code={access_code}"
        )

        for record in records:
            # Match status and room number
            if record.get("status") != expected_status or record.get("room_No") != unit_number:
                continue

            # Match access code based on direction
            if put_in:
                # For put-in: code is in in_staff_ID field (e.g. "AA986725")
                in_staff_id = record.get("in_staff_ID", "")
                record_code = in_staff_id[2:] if len(in_staff_id) > 2 else in_staff_id
            else:
                # For take-out: code is in pin field (e.g. "467934")
                record_code = record.get("pin", "")

            if record_code != access_code:
                logger.debug(
                    f"Code mismatch: record_code={record_code}, expected={access_code}"
                )
                continue

            # Match found — parse event time
            process_time = record.get("process_time", "")
            event_datetime = None
            if process_time:
                jst_datetime = datetime.strptime(process_time, "%Y%m%d%H%M%S")
                event_datetime = jst_datetime - timedelta(hours=9)
            else:
                event_datetime = get_current_time()

            logger.info(
                f"Found matching Galilei record: status={expected_status}, "
                f"room_No={record.get('room_No')}, code={record_code}, "
                f"process_time={process_time}"
            )
            return True, event_datetime

        logger.warning(
            f"No matching Galilei record found for unit {locker_unit.full_unit_number}, "
            f"code={access_code}, status={expected_status}"
        )
        return False, None

    except Exception as e:
        logger.error(f"Failed to query Galilei door activity: {str(e)}")
        return False, None


def _get_active_galilei_access_codes_in_location(locker_unit: LockerUnit, db: Session) -> set:
    """Collect all access codes currently in use across the same locker location."""
    from apps.orders.crud import get_pickup_codes_by_locker_units

    unit_ids = db.exec(
        select(LockerUnit.id).where(LockerUnit.location_id == locker_unit.location_id)
    ).all()

    if not unit_ids:
        return set()

    order_codes = get_pickup_codes_by_locker_units(db, unit_ids, status=ORDER_STATUS_READY_FOR_PICKUP)
    reservation_codes = get_access_codes_by_locker_units_and_combo_status(
        db, unit_ids, combo_status=COMBO_STATUS_PREPARATION_TO_LOCKER
    )

    return set(order_codes) | set(reservation_codes)


def verify_access_code(access_code: str, locker_unit: LockerUnit, db: Session) -> bool:
    """
    Verify that the generated access code (with AA/BB prefix) does not conflict
    with any PIN currently active on the Galilei cloud within the same locker location.

    Only codes tied to active states are live on Galilei:
      - order.pickup_code   where order.status = READY_FOR_PICKUP
      - reservation.access_code  where combo.status = PREPARATION_TO_LOCKER

    Codes in any other state have already been deactivated (removed) on Galilei
    when their status transitioned. Setting a duplicate PIN would overwrite an
    active code on the hardware, so this check must pass before calling the
    Galilei API.

    Returns True if the code is safe to use, False if it collides with an active PIN.
    """
    stripped = access_code[2:]
    active_codes = _get_active_galilei_access_codes_in_location(locker_unit, db)
    return stripped not in active_codes


def generate_access_code_service(
    locker_unit: Optional[LockerUnit], put_in: bool, db: Optional[Session] = None
):
    """Generate a new access code for locker reservation"""

    # Add random delay between 0.5 and 2 seconds to avoid rate limiting
    delay = random.uniform(0.5, 2.0)
    logger.info(f"Adding random delay of {delay:.2f}s before generating access code")
    time.sleep(delay)

    logger.info(
        f"Starting generate_access_code_service - unit_number: {locker_unit.unit_number if locker_unit else 'None'}, put_in: {put_in}"
    )

    try:
        for attempt in range(MAX_ACCESS_CODE_RETRIES):
            if put_in:
                access_code = generate_access_code_in()
            else:
                access_code = generate_access_code_out()

            if db is None or locker_unit is None or verify_access_code(access_code, locker_unit, db):
                break

            logger.warning(
                f"Access code {access_code[2:]} already in use, regenerating "
                f"(attempt {attempt + 1}/{MAX_ACCESS_CODE_RETRIES})"
            )

        logger.info(f"Generated access_code: {access_code}")

        # Galilei mode '0' - Production, call to Galilei
        if os.getenv("GALILEI_MODE") == "0":
            url = galilei_service.get_changes_access_code_url()
            door_no = str(locker_unit.unit_number)
            topic_name = str(locker_unit.topic_name) if locker_unit.topic_name else None
            if not topic_name or topic_name == "None":
                raise locker_unit_topic_name_missing()

            data = {
                "topic_name": topic_name,
                "pin_No": access_code,
                "door_No": door_no if door_no else "1",
            }

            logger.info(f"Calling Galilei API - URL: {url}, Data: {data}")

            auth_response = authenticate_locker_user()
            id_token = auth_response["AuthenticationResult"]["IdToken"]
            logger.info(f"Authentication successful, token length: {len(id_token)}")

            headers = {"Authorization": f"Bearer {id_token}"}

            logger.info(f"Sending POST request to Galilei API...")
            response = requests.post(url, json=data, headers=headers, timeout=10)

            logger.info(
                f"Galilei API response - Status: {response.status_code}, Body: {response.text}"
            )

            response.raise_for_status()
            logger.info(f"Successfully generated access code for unit {door_no}")

        return access_code

    except requests.exceptions.Timeout as e:
        logger.error(
            f"Timeout calling Galilei API for unit {locker_unit.unit_number if locker_unit else 'None'}: {e}"
        )
        raise
    except requests.exceptions.RequestException as e:
        logger.error(
            f"Request error calling Galilei API for unit {locker_unit.unit_number if locker_unit else 'None'}: {e}"
        )
        if hasattr(e, "response") and e.response is not None:
            logger.error(
                f"Error response status: {e.response.status_code}, body: {e.response.text}"
            )
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error in generate_access_code_service for unit {locker_unit.unit_number if locker_unit else 'None'}: {e}",
            exc_info=True,
        )
        raise


# ===== LockerLocation Services =====
def list_locker_locations_service(
    db: Session,
    owner_id: Optional[str] = None,
    user=None,
    limit: int = 20,
    offset: int = 0,
):
    """List locker locations with role-based filtering"""

    if not user:
        # No user provided, return empty list
        return [], 0

    if user.role == "admin":
        if not owner_id:
            raise owner_locker_id_required()
        locations, total = get_locker_locations(
            db, owner_id=owner_id, limit=limit, offset=offset
        )

    # Shop owner role: get lockers associated with their shop
    elif user.role == "owner_shop":
        associated_shop = user.get_associated_shop()
        if not associated_shop:
            # If user has no associated shop, return empty list
            return [], 0

        locations, total = get_locker_locations(
            db, shop_id=associated_shop.id, limit=limit, offset=offset
        )

    # Locker owner role: get lockers they own
    elif user.role == "owner_locker":
        locations, total = get_locker_locations(
            db, owner_id=user.id, limit=limit, offset=offset
        )

    else:
        # For other roles, return empty list
        return [], 0

    return (
        [build_locker_location_response(db, loc) for loc in locations],
        total,
    )


def list_public_locker_locations_service(
    db: Session,
    limit: int = 20,
    offset: int = 0,
    user_lat: Optional[str] = None,
    user_lng: Optional[str] = None,
    user_id: Optional[str] = None,
    is_selling_combo: Optional[bool] = None,
    search: Optional[str] = None,
):
    """List active locker locations that have at least one registered shop."""

    user_location: Optional[str] = None
    if user_lat and user_lng:
        user_location = f"{user_lat},{user_lng}"

    # Get only active locations that have at least one registered shop
    locations = get_public_locker_locations(db, search=search)

    location_ids = [loc.id for loc in locations]
    combos_count_by_location_id: dict[str, int] = {}
    if location_ids:
        # Calculate number of combos with status = 'SELLING' for all locations (batch query)
        combos_count_stmt = (
            select(LockerUnit.location_id, func.count(Combo.id))
            .select_from(Combo)
            .join(LockerReservation, LockerReservation.combo_id == Combo.id)
            .join(LockerUnit, LockerUnit.id == LockerReservation.locker_unit_id)
            .where(
                LockerUnit.location_id.in_(location_ids),
                Combo.status == COMBO_STATUS_SELLING,
            )
            .group_by(LockerUnit.location_id)
        )
        combos_count_by_location_id = {
            str(location_id): int(count)
            for location_id, count in db.exec(combos_count_stmt).all()
        }

    # Filter locations that have selling combos if is_selling_combo=True
    if is_selling_combo:
        locations = [
            loc
            for loc in locations
            if combos_count_by_location_id.get(str(loc.id), 0) > 0
        ]
        location_ids = [loc.id for loc in locations]

    total = len(locations)

    # Batch query user's favorites for this page's location_ids
    favorite_by_location: dict[str, tuple[bool, int]] = {}
    if user_id and location_ids:
        favs = get_favorite_lockers_by_user_and_locations(db, user_id, location_ids)
        for fav in favs:
            favorite_by_location[str(fav.locker_location_id)] = (
                True,
                fav.sort_order,
            )

    responses = []
    for loc in locations:
        data = LockerLocationPublicRead.model_validate(loc, from_attributes=True)

        data.number_combos = combos_count_by_location_id.get(str(loc.id), 0)

        if user_location and loc.position:
            data.distance = get_distance(user_location, loc.position)
        else:
            data.distance = None

        fav_info = favorite_by_location.get(str(loc.id))
        if fav_info:
            data.is_favorite = True
            data.favorite_sort_order = fav_info[1]
        else:
            data.is_favorite = False
            data.favorite_sort_order = None

        responses.append(data)

    # Sort rules:
    # 1) If user_location exists -> sort by distance ASC (None distances go last)
    # 2) If no user_location -> sort by number_combos DESC, but all 0 go last
    if user_location:
        responses.sort(
            key=lambda x: (
                x.distance is None,
                x.distance if x.distance is not None else float("inf"),
            )
        )
    else:
        responses.sort(
            key=lambda x: (
                (x.number_combos or 0) == 0,
                -(x.number_combos or 0),
            )
        )

    # Apply pagination AFTER sorting to keep ordering consistent across pages
    paginated_responses = responses[offset : offset + limit]
    return (paginated_responses, total)


def _calculate_location_foodloss_today(db: Session, location_id: str):
    """Calculate foodloss (kg) and co2_reduction (kg) from orders placed today (JST) at this location"""
    from datetime import datetime, timedelta, timezone

    from apps.orders.crud import get_orders_by_locker_units_and_date_range
    from apps.products.crud import get_foodloss_grams_by_combo_ids

    JST = timezone(timedelta(hours=9))
    now_jst = datetime.now(JST)
    today_start_utc = now_jst.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    today_end_utc = now_jst.replace(hour=23, minute=59, second=59, microsecond=999999).astimezone(timezone.utc)

    units, _ = get_locker_units(db, location_id=location_id, limit=10000)
    unit_ids = [u.id for u in units]
    if not unit_ids:
        return 0.0, 0.0

    orders_today = get_orders_by_locker_units_and_date_range(db, unit_ids, today_start_utc, today_end_utc)
    combo_ids = [o.combo_id for o in orders_today]

    foodloss_grams = get_foodloss_grams_by_combo_ids(db, combo_ids)
    foodloss_kg = round(foodloss_grams / 1000, 4)
    return foodloss_kg, round(foodloss_kg * 2.5, 4)


def get_locker_location_service(
    location_id: str,
    db: Session,
    user_lat: Optional[str] = None,
    user_lng: Optional[str] = None,
):
    """Get a locker location by ID with all its units"""
    location = get_locker_location_by_id(db, location_id)
    if not location:
        raise locker_location_not_found()

    # Build user_location string only if both lat and lng are provided
    user_location = None
    if user_lat and user_lng:
        user_location = f"{user_lat},{user_lng}"

    response = build_locker_location_with_units_response(db, location, user_location)
    response.foodloss, response.co2_reduction = _calculate_location_foodloss_today(db, location_id)
    return response


def create_locker_location_service(location: LockerLocationCreate, user, db: Session):
    """Create a new locker location"""
    # Validate location creation
    validate_location_creation(location, user, db)

    # Create location (exclude shop_ids from the model dump)
    location_data = location.model_dump(exclude={"shop_ids"})
    location_data["owner_id"] = str(user.id)

    # Auto-generate code if not provided
    if not location_data.get("code"):
        location_data["code"] = generate_location_code(db, location.name)

    db_location = LockerLocation(**location_data)
    db_location = create_locker_location(db, db_location)

    # Associate shops if provided
    if location.shop_ids:
        from apps.lockers.models.shop_locker_association import ShopLockerAssociation
        from apps.shops.crud import get_shop

        for shop_id in location.shop_ids:
            # Verify shop exists (should already be validated)
            shop = get_shop(db, shop_id)
            if shop:
                association = ShopLockerAssociation(
                    shop_id=shop_id, locker_location_id=db_location.id
                )
                db.add(association)

        db.commit()
        db.refresh(db_location)

    # Build response with shop_ids using helper function
    return build_locker_location_response(db, db_location)


def update_locker_location_service(
    location_id: str, update_data: "LockerLocationUpdate", user, db: Session
):
    """Update an existing locker location"""
    from apps.lockers.crud import get_locker_location_by_id
    from apps.lockers.models.shop_locker_association import ShopLockerAssociation
    from apps.shops.crud import get_shop

    # Get existing location
    db_location = get_locker_location_by_id(db, location_id)
    if not db_location:
        raise locker_location_not_found()

    if not can_manage_locker(user, db_location):
        raise insufficient_permissions()

    # Update basic fields
    update_dict = update_data.model_dump(exclude_unset=True, exclude={"shop_ids"})
    for field, value in update_dict.items():
        setattr(db_location, field, value)

    # Handle shop associations update
    if update_data.shop_ids is not None:
        # Validate new shop associations
        if update_data.shop_ids:
            for shop_id in update_data.shop_ids:
                shop = get_shop(db, shop_id)
                if not shop:
                    from apps.shops.exceptions import shop_not_found

                    raise shop_not_found()

        # Remove existing associations
        existing_associations = db.exec(
            select(ShopLockerAssociation).where(
                ShopLockerAssociation.locker_location_id == location_id
            )
        ).all()

        # Delete existing associations
        for association in existing_associations:
            db.delete(association)

        # Add new associations
        for shop_id in update_data.shop_ids:
            association = ShopLockerAssociation(
                shop_id=shop_id, locker_location_id=location_id
            )
            db.add(association)

    db.commit()
    db.refresh(db_location)

    return build_locker_location_response(db, db_location)


# ===== LockerUnit Services =====
def get_locker_unit_service(unit_id: str, user, db: Session):
    """Get a locker unit by ID"""
    unit = get_locker_unit_by_id(db, unit_id)
    if not unit:
        raise locker_unit_not_found()

    return LockerUnitRead.model_validate(unit, from_attributes=True)


def list_locker_units_service(
    db: Session,
    location_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
):
    """List locker units with optional filtering"""
    units, total = get_locker_units(
        db,
        location_id=location_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return (
        [LockerUnitRead.model_validate(unit, from_attributes=True) for unit in units],
        total,
    )


def create_locker_unit_service(unit: LockerUnitCreate, user, db: Session):
    """Create a new locker unit"""
    # Validate unit creation
    validate_unit_creation(unit, user, db)

    # Create unit
    db_unit = LockerUnit(**unit.model_dump())
    db_unit = create_locker_unit(db, db_unit)
    return LockerUnitRead.model_validate(db_unit, from_attributes=True)


def update_locker_unit_service(unit_id: str, unit: LockerUnitUpdate, user, db: Session):
    """Update a locker unit"""
    # Validate unit access
    existing_unit, location = validate_unit_access(unit_id, user, db)

    # Update unit
    update_data = unit.model_dump(exclude_unset=True)
    updated_unit = update_locker_unit(db, unit_id, update_data)

    return LockerUnitRead.model_validate(updated_unit, from_attributes=True)


def delete_locker_unit_service(unit_id: str, user, db: Session):
    """Delete a locker unit"""
    # Validate unit access
    unit, location = validate_unit_access(unit_id, user, db)

    # Delete unit
    success = delete_locker_unit(db, unit_id)
    return {"success": success}


# ===== LockerReservation Services =====
def get_locker_reservation_service(reservation_id: str, user, db: Session):
    """Get a locker reservation by ID"""
    reservation = get_locker_reservation_by_id(db, reservation_id)
    if not reservation:
        raise locker_reservation_not_found()

    # Validate access permissions
    validate_reservation_access(reservation, user)

    return create_reservation_read_with_qr_code(reservation)


def create_locker_reservation_service(
    reservation: LockerReservationCreate, user, db: Session
):
    """Create a new locker reservation with timing logic and cooldown check"""
    from apps.lockers.tasks import check_preparation_timeout_task

    # TODO add timesleep about 1s
    time.sleep(1)

    # Check if shop is in cooldown period
    user_shop = user.get_associated_shop()
    shop_id = user_shop.id if user_shop else user.id

    validate_shop_cooldown(user.id, db)
    validate_unit_availability_immediate(reservation.locker_unit_id, db)
    get_locker_unit_by_id(db, reservation.locker_unit_id)

    # Access code will be generated later when combo is published (draft -> public)
    # For now, create reservation without access code
    access_code = None

    # Calculate timing for combo placement and sale
    preparation_deadline = get_current_time() + timedelta(
        minutes=COMBO_PREPARATION_TIME_MINUTES
    )

    # Create reservation with timing data first
    reservation_data = reservation.model_dump()
    db_reservation = LockerReservation(
        **reservation_data,
        user_id=user.id,
        shop_id=shop_id,
        status=RESERVATION_STATUS_PENDING,
        access_code=access_code,
        preparation_deadline=preparation_deadline,
        sale_end_time=None,
        price_reduction_time=None,
    )
    db_reservation = create_locker_reservation(db, db_reservation)

    # Update unit status to RESERVED using the proper service function
    update_locker_unit(db, reservation.locker_unit_id, {"status": UNIT_STATUS_RESERVED})

    # Schedule task to check preparation timeout (20 minutes from now)
    check_preparation_timeout_task.apply_async(
        args=[str(db_reservation.id)], eta=preparation_deadline
    )

    notification_time = preparation_deadline - timedelta(minutes=5)
    # Schedule placement deadline approaching notification (5 minutes before deadline)
    from apps.integrations.celery.shops.tasks import send_deadline_put_to_locker

    if notification_time > get_current_time():
        send_deadline_put_to_locker.apply_async(
            args=[str(db_reservation.id), str(user.id)], eta=notification_time
        )

    sync_location_to_firebase_task.delay(
        str(db_reservation.locker_unit_id), is_unit_id=True
    )

    return create_reservation_read_with_qr_code(db_reservation)


def update_locker_reservation_service(
    reservation_id: str, reservation: LockerReservationUpdate, user, db: Session
):
    """Update a locker reservation (confirm pushed stuffs to locker box)"""
    # Validate reservation exists and is not expired
    existing_reservation = get_locker_reservation_by_id(db, reservation_id)
    if not existing_reservation:
        raise locker_reservation_not_found()

    if existing_reservation.locker_unit_id != reservation.locker_unit_id:
        raise changing_locker_unit_id_not_allowed()

    if existing_reservation.preparation_deadline < get_current_time():  # type: ignore
        raise reservation_expired()

    # Validate access permissions
    validate_reservation_access(existing_reservation, user)

    # Prepare and apply updates
    update_data = reservation.model_dump(exclude_unset=True)
    if "status" in update_data and update_data["status"]:
        update_data["status"] = update_data["status"].upper()

    updated_reservation = update_locker_reservation(db, reservation_id, update_data)

    # Handle status-related updates if status was changed
    if updated_reservation and "status" in update_data:
        new_status = update_data["status"]

        # Handle combo activation for ACTIVE status
        if new_status == "ACTIVE":
            locker_unit = get_locker_unit_by_id(db, updated_reservation.locker_unit_id)
            # if os.getenv("GALILEI_MODE") == "1":
            #     locker_unit = get_locker_unit_by_id(
            #         db, updated_reservation.locker_unit_id
            #     )
            #     res = get_locker_status_service(
            #         full_unit_number=locker_unit.full_unit_number,
            #         from_date=(get_current_time() - timedelta(minutes=5) + timedelta(hours=9)).strftime(
            #             "%Y%m%d%H%M%S"
            #         ),
            #         to_date=(get_current_time() + timedelta(hours=9)).strftime("%Y%m%d%H%M%S"),
            #     )
            #     if res and len(res) > 0:
            #         # Check if any status indicates the unit is properly occupied
            #         valid_status_found = False
            #         unit_number = locker_unit.unit_number

            #         if not unit_number.startswith("0"):
            #             unit_number = "0" + unit_number

            #         for res_status in res:
            #             # Unit should have status "1" (occupied) AND correct staff ID
            #             if (
            #                 res_status.get("status") == "1"
            #                 and res_status.get("room_No") == unit_number
            #             ):
            #                 valid_status_found = True
            #                 break
            #         if not valid_status_found:
            #             raise locker_unit_empty()

            #         # Generate new access code once after validation
            #         generate_access_code_service(locker_unit, put_in=True)
            #     else:
            #         raise locker_unit_empty()
            #       generate_access_code_service(locker_unit, put_in=True)

            # if os.getenv("GALILEI_MODE") == "0":
            #     _remove_galilei_code(locker_unit.unit_number, put_in=False)

            handle_combo_activation(db, updated_reservation, reservation_id)
            update_unit_status_from_reservation(db, updated_reservation, new_status)

    return create_reservation_read_with_qr_code(updated_reservation)


def cancel_locker_reservation_service(reservation_id: str, user, db: Session):
    """Cancel a locker reservation"""
    # TODO add time sleep about 1s
    time.sleep(1)

    reservation = get_locker_reservation_by_id(db, reservation_id)
    if not reservation:
        raise locker_reservation_not_found()

    # Validate access permissions
    validate_reservation_access(reservation, user)

    # Cancel reservation
    success = cancel_locker_reservation(db, reservation_id)

    # Update unit status back to available when reservation is cancelled
    if success:
        update_locker_unit(
            db, reservation.locker_unit_id, {"status": UNIT_STATUS_AVAILABLE}
        )

    # Cancel reservation
    sync_location_to_firebase_task.delay(reservation.locker_unit_id, is_unit_id=True)

    return {"success": success}


# ===== Special Actions Services =====
def check_availability_service(request: CheckAvailabilityRequest, db: Session):
    """Check availability of locker units for immediate booking"""
    available_units = get_available_units_immediate(
        db,
        request.location_id,
        request.size,
    )

    # Get location for context
    location = get_locker_location_by_id(db, request.location_id)
    if not location:
        raise locker_location_not_found()

    # Format response
    responses = []
    for unit in available_units:
        price = calculate_locker_price(unit.size)
        responses.append(
            AvailableUnitResponse(
                unit_id=unit.id,
                unit_number=unit.unit_number,
                size=unit.size,
                location_name=location.name,
                estimated_price=price,
            )
        )

    return responses


def get_reservation_timing_info(reservation_id: str, db: Session):
    """Get timing information for a reservation"""
    from apps.lockers.timing import get_current_combo_status, get_time_remaining_info

    reservation = get_locker_reservation_by_id(db, reservation_id)
    if not reservation:
        raise locker_reservation_not_found()

    # Get time remaining info
    timing_info = get_time_remaining_info(
        preparation_deadline=reservation.preparation_deadline,
        sale_end_time=reservation.sale_end_time,
        price_reduction_time=reservation.price_reduction_time,
        item_deposited_at=reservation.item_deposited_at,
    )

    # Get current status if combo exists
    current_status = None
    if (
        reservation.combo
        and reservation.created_at
        and reservation.preparation_deadline
    ):
        current_status = get_current_combo_status(
            reservation_created_at=reservation.created_at,
            preparation_deadline=reservation.preparation_deadline,
            item_deposited_at=reservation.item_deposited_at,
            sale_end_time=reservation.sale_end_time,
            price_reduction_time=reservation.price_reduction_time,
            current_status=reservation.combo.status if reservation.combo else "unknown",
        )

    return {
        "reservation_id": reservation_id,
        "timing_info": timing_info,
        "current_combo_status": current_status,
        "preparation_deadline": reservation.preparation_deadline,
        "sale_end_time": reservation.sale_end_time,
        "price_reduction_time": reservation.price_reduction_time,
        "item_deposited_at": reservation.item_deposited_at,
    }


def check_shop_cooldown_service(shop_id: str, db: Session):
    """Check if a shop is currently in cooldown period"""
    from apps.lockers.crud import get_active_shop_cooldown
    from apps.lockers.timing import get_cooldown_remaining_time

    active_cooldown = get_active_shop_cooldown(db, shop_id)

    if not active_cooldown:
        return {
            "shop_id": shop_id,
            "in_cooldown": False,
            "can_reserve": True,
            "message": "No active cooldown",
        }

    cooldown_info = get_cooldown_remaining_time(active_cooldown.cooldown_end)

    return {
        "shop_id": shop_id,
        "cooldown_reason": active_cooldown.reason,
        "failed_reservation_id": active_cooldown.failed_reservation_id,
        "cooldown_start": active_cooldown.cooldown_start,
        **cooldown_info,
    }


def collect_item_service(request: CollectItemRequest, user, db: Session):
    """Mark item as collected from locker"""
    reservation = get_locker_reservation_by_id(db, request.reservation_id)
    if not reservation:
        raise locker_reservation_not_found()

    # Validate access code and collect action
    validate_access_code(reservation, request.access_code)
    validate_collect_action(reservation)

    # Update reservation
    update_data = {
        "item_collected_at": get_current_time(),
        "status": RESERVATION_STATUS_COMPLETED,
    }
    updated_reservation = update_locker_reservation(
        db, request.reservation_id, update_data
    )

    # Update unit status to available (per spec - locker unit becomes available after pickup)
    update_locker_unit(
        db, reservation.locker_unit_id, {"status": UNIT_STATUS_AVAILABLE}
    )

    return create_reservation_read_with_qr_code(updated_reservation)


# ===== Unit Status Management Services =====
def set_unit_status_service(unit_id: str, status: str, user, db: Session):
    """Set unit status for maintenance operations"""
    from fastapi import HTTPException

    from apps.core.constants import UNIT_STATUS_CHOICES

    # Validate status
    if status not in UNIT_STATUS_CHOICES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {UNIT_STATUS_CHOICES}",
        )

    # Validate unit access
    unit, location = validate_unit_access(unit_id, user, db)

    # Update unit status
    updated_unit = update_locker_unit(db, unit_id, {"status": status})

    return LockerUnitRead.model_validate(updated_unit, from_attributes=True)


def complete_cleaning_service(unit_id: str, user, db: Session):
    """Mark unit maintenance as completed and set status back to available"""
    from fastapi import HTTPException

    # Validate unit access
    unit, location = validate_unit_access(unit_id, user, db)

    # Check if unit is in maintenance status (since cleaning status doesn't exist in spec)
    if unit.status != "maintenance":
        raise HTTPException(
            status_code=400,
            detail="Unit must be in maintenance status to complete maintenance",
        )

    # Set status back to available
    updated_unit = update_locker_unit(db, unit_id, {"status": UNIT_STATUS_AVAILABLE})

    return LockerUnitRead.model_validate(updated_unit, from_attributes=True)


# ===== LockerUnit Temperature Services =====
def set_temperature_by_column_service(
    location_id: str, column_index: int, temperature: Optional[str], user, db: Session
):
    """Set temperature for all locker units in a specific column of a location"""
    from apps.core.constants import MAX_LOCKER_COLUMN
    from sqlmodel import select

    location = get_locker_location_by_id(db, location_id)
    if not location:
        raise locker_location_not_found()

    if user.role != "admin" and not can_manage_locker(user, location):
        raise insufficient_permissions()

    if not (1 <= column_index <= MAX_LOCKER_COLUMN):
        raise column_index_out_of_range(MAX_LOCKER_COLUMN)

    if temperature is not None:
        try:
            temp_value = float(temperature)
            if not (-20 <= temp_value <= 15):
                raise temperature_out_of_range(temperature)
        except ValueError:
            raise temperature_not_numeric(temperature)

    units = db.exec(
        select(LockerUnit).where(LockerUnit.location_id == location_id, LockerUnit.column_index == column_index)
    ).all()

    if not units:
        raise locker_units_not_found_for_column(column_index)

    updated = []
    for unit in units:
        updated_unit = update_locker_unit(db, unit.id, {"temperature": temperature})
        sync_location_to_firebase_task.delay(unit.id, is_unit_id=True)
        updated.append(LockerUnitRead.model_validate(updated_unit, from_attributes=True))

    return updated


# ===== Favorite Locker (My Locker) Services =====


def add_favorite_locker_service(
    db: Session, user_id: str, locker_location_id: str
) -> dict:
    """
    Add a locker location to user's favorites (max 3).

    Args:
        db: Database session
        user_id: User ID
        locker_location_id: Locker location ID to add

    Returns:
        Dict with action "added"

    Raises:
        locker_location_not_found: Location not found or inactive
        favorite_locker_limit_reached: User already has 3 favorites
    """
    location = get_locker_location_by_id(db, locker_location_id)
    if not location or not location.is_active:
        raise locker_location_not_found()

    existing = get_favorite_locker_by_user_and_location(db, user_id, locker_location_id)
    if existing:
        return

    count = count_favorite_lockers_by_user(db, user_id)
    if count >= MAX_FAVORITE_LOCKERS:
        raise favorite_locker_limit_reached()

    sort_order = count + 1
    create_favorite_locker(db, user_id, locker_location_id, sort_order)


def remove_favorite_locker_service(
    db: Session, user_id: str, locker_location_id: str
) -> dict:
    """
    Remove a locker location from user's favorites.

    Args:
        db: Database session
        user_id: User ID
        locker_location_id: Locker location ID to remove

    Returns:
        Dict with action "removed"

    Raises:
        favorite_locker_not_found: Not in user's list
    """
    fav = get_favorite_locker_by_user_and_location(db, user_id, locker_location_id)
    if not fav:
        raise favorite_locker_not_found()

    delete_favorite_locker(db, fav)


def list_favorite_lockers_service(
    db: Session,
    user_id: str,
    user_lat: Optional[str] = None,
    user_lng: Optional[str] = None,
) -> List[FavoriteLockerRead]:
    """
    List user's favorite lockers ordered by sort_order, with location details.

    Args:
        db: Database session
        user_id: User ID
        user_lat: Optional user latitude for distance
        user_lng: Optional user longitude for distance

    Returns:
        List of FavoriteLockerRead
    """
    favorites = list_favorite_lockers_by_user(db, user_id)
    user_location = f"{user_lat},{user_lng}" if (user_lat and user_lng) else None
    result: List[FavoriteLockerRead] = []

    for fav in favorites:
        loc = fav.locker_location
        if not loc:
            continue

        distance = None
        if user_location and loc.position:
            distance = get_distance(user_location, loc.position)

        position_parsed = None
        if loc.position:
            try:
                position_parsed = parse_position_string(loc.position)
            except (ValueError, IndexError):
                pass

        result.append(
            FavoriteLockerRead(
                id=fav.id,
                locker_location_id=fav.locker_location_id,
                sort_order=fav.sort_order,
                favorited_at=fav.favorited_at,
                last_used_at=fav.last_used_at,
                name=loc.name,
                address=loc.address,
                position=position_parsed,
                image=loc.image,
                distance=distance,
            )
        )

    return result


def reorder_favorite_lockers_service(
    db: Session, user_id: str, locker_location_ids: List[str]
) -> None:
    """
    Update sort order of user's favorite lockers.

    Args:
        db: Database session
        user_id: User ID
        locker_location_ids: List of location IDs in new order (first = priority 1)

    Raises:
        favorite_locker_reorder_invalid: IDs do not match current favorites
    """
    current = list_favorite_lockers_by_user(db, user_id)
    current_ids = {f.locker_location_id for f in current}
    requested_ids = set(locker_location_ids)

    if requested_ids != current_ids or len(locker_location_ids) != len(current):
        raise favorite_locker_reorder_invalid()

    update_sort_order_for_user(db, user_id, locker_location_ids)


def sync_from_guest_service(
    db: Session, user_id: str, locker_location_ids: List[str]
) -> SyncFromGuestResponse:
    """
    Sync local (guest) favorite lockers to the user account.

    Rules:
    - If 3 local lockers are passed: replace all existing server favorites with the 3 local ones.
    - If < 3 local lockers are passed: merge local with server favorites.
        - Local lockers come first (priority).
        - Fill remaining slots from server favorites sorted by most recent last_used_at.
        - Deduplicate; total capped at MAX_FAVORITE_LOCKERS (3).

    Args:
        db: Database session
        user_id: User ID
        locker_location_ids: List of location IDs from local/guest (max 3)

    Returns:
        SyncFromGuestResponse with synced=True and notification text if changes were made.
    """
    local_ids = list(locker_location_ids)[:MAX_FAVORITE_LOCKERS]

    if not local_ids:
        return SyncFromGuestResponse(synced=False)

    # Validate local locations: raise if ID not found in DB, skip if inactive
    valid_local_ids: List[str] = []
    for loc_id in local_ids:
        location = get_locker_location_by_id(db, loc_id)
        if not location:
            raise locker_location_not_found()
        if location.is_active:
            valid_local_ids.append(loc_id)

    if not valid_local_ids:
        return SyncFromGuestResponse(synced=False)

    # Fetch current server favorites once (used for both merge and no-op check)
    server_favs = list_favorite_lockers_by_user(db, user_id)
    current_ids = [f.locker_location_id for f in server_favs]

    if len(local_ids) >= MAX_FAVORITE_LOCKERS:
        # Replace: use local list only
        final_ids = valid_local_ids[:MAX_FAVORITE_LOCKERS]
    else:
        # Merge: local first, then fill from server sorted by most recent last_used_at
        server_favs_sorted = sorted(
            server_favs,
            key=lambda f: f.last_used_at or f.favorited_at,
            reverse=True,
        )

        final_ids = list(valid_local_ids)
        seen = set(final_ids)
        for fav in server_favs_sorted:
            if len(final_ids) >= MAX_FAVORITE_LOCKERS:
                break
            if fav.locker_location_id not in seen:
                seen.add(fav.locker_location_id)
                final_ids.append(fav.locker_location_id)

    # No changes needed if the final list is identical to the current server favorites
    if final_ids == current_ids:
        return SyncFromGuestResponse(synced=False)

    # Build lookup map from existing favorites
    existing_map = {f.locker_location_id: f for f in server_favs}
    final_ids_set = set(final_ids)

    # Delete only favorites that are no longer in the final list
    for fav in server_favs:
        if fav.locker_location_id not in final_ids_set:
            db.delete(fav)
    db.commit()

    # Update sort_order for kept ones, create new ones
    for sort_order, loc_id in enumerate(final_ids, start=1):
        if loc_id in existing_map:
            existing_map[loc_id].sort_order = sort_order
        else:
            create_favorite_locker(db, user_id, loc_id, sort_order)
    db.commit()

    return SyncFromGuestResponse(
        synced=True,
        title="マイロッカーを同期しました",
        message="この端末の設定を優先して保存しました。",
    )


# ===== Search History Services =====


def add_search_history_service(
    db: Session, user_id: str, locker_location_id: str
) -> None:
    """Add or update a locker location in user's search history (max 5)."""
    location = get_locker_location_by_id(db, locker_location_id)
    if not location:
        raise locker_location_not_found()

    existing = get_search_history_by_user_and_location(db, user_id, locker_location_id)
    if existing:
        update_search_history_searched_at(db, existing)
        return

    count = count_search_history_by_user(db, user_id)
    if count >= MAX_SEARCH_HISTORY_LOCKERS:
        oldest = get_oldest_search_history_by_user(db, user_id)
        if oldest:
            delete_search_history(db, oldest)

    create_search_history(db, user_id, locker_location_id)


def list_search_history_service(
    db: Session, user_id: str
) -> list[SearchHistoryRead]:
    """List user's search history, newest first."""
    records = list_search_history_by_user(db, user_id)
    result = []
    for record in records:
        location = get_locker_location_by_id(db, record.locker_location_id)
        result.append(
            SearchHistoryRead(
                locker_location_id=record.locker_location_id,
                name=location.name if location else None,
                searched_at=record.searched_at,
            )
        )
    return result
