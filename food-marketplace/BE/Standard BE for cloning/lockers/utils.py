import io
import secrets
import string
from datetime import timedelta
from typing import Optional

import qrcode
from sqlmodel import Session, select

from apps.core.constants import COMBO_STATUS_SELLING
from apps.core.logging import logger
from apps.integrations.aws.s3 import upload_file_to_s3
from apps.lockers.models.reservation import LockerReservation
from apps.products.utils import (
    count_shop_pending_combos,
    sync_shop_combo_count_to_firebase,
)

from .crud import update_locker_reservation, update_locker_unit
from .schemas import (
    LockerLocationRead,
    LockerLocationWithUnits,
    LockerReservationRead,
    LockerUnitRead,
    ShopMinimalRead,
)


def _build_and_upload_qr_code(access_code: str, reservation_id: str) -> Optional[str]:
    """Build QR code image for access_code, upload to S3, and return the URL."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(access_code)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img_bytes = io.BytesIO()
    img.save(img_bytes, "PNG")
    img_bytes.seek(0)

    filename = f"locker_access_codes/{reservation_id}_{access_code}.png"
    return upload_file_to_s3(img_bytes, filename)


def generate_and_save_qr_code_url(reservation: LockerReservation, db: Session) -> Optional[str]:
    """
    Generate a QR code image for the reservation's access_code, upload to S3,
    persist the URL in the DB, and return the URL.
    Should be called once when access_code is first assigned.
    Returns None if no access_code is available.
    """
    if not reservation.access_code:
        return None

    try:
        s3_url = _build_and_upload_qr_code(reservation.access_code, str(reservation.id))

        reservation.qr_code_url = s3_url
        db.add(reservation)
        db.commit()

        logger.info(f"QR code saved for reservation {reservation.id}")
        return s3_url

    except Exception as e:
        logger.error(f"Failed to generate QR code for reservation {reservation.id}: {e}")
        return None


def generate_qr_code_url(access_code: str, reservation_id: str) -> Optional[str]:
    """
    Generate a QR code image for the given access_code, upload to S3, and return the URL.
    Does NOT persist anything to the DB.
    """
    try:
        s3_url = _build_and_upload_qr_code(access_code, reservation_id)
        logger.info(f"QR code generated for reservation {reservation_id}")
        return s3_url

    except Exception as e:
        logger.error(f"Failed to generate QR code for reservation {reservation_id}: {e}")
        return None


def generate_access_code_in(length: int = 8) -> str:
    """Generate a random access code for locker reservation starting with 'AA' followed by numbers"""
    # Ensure length is between 6 and 12 characters total
    length = max(6, min(8, length))

    # Generate random numbers for the remaining length (total - 2 for 'AA' prefix)
    numbers_length = length - 2
    numbers = "".join(secrets.choice(string.digits) for _ in range(numbers_length))

    return f"AA{numbers}"


def generate_access_code_out(length: int = 8) -> str:
    """Generate a random access code for locker reservation starting with 'BB' followed by numbers"""
    # Ensure length is between 6 and 12 characters total
    length = max(6, min(8, length))

    # Generate random numbers for the remaining length (total - 2 for 'BB' prefix)
    numbers_length = length - 2
    numbers = "".join(secrets.choice(string.digits) for _ in range(numbers_length))

    return f"BB{numbers}"


def generate_access_reset_code(put_in: bool = True) -> str:
    """Generate a reset code with 'AA' prefix for put_in and 'BB' for take_out"""
    if put_in:
        prefix = "AA"
    else:
        prefix = "BB"

    return prefix


def calculate_locker_price(size: str) -> float:
    """Calculate base price for locker reservation based on size"""
    # Base pricing per usage (real-time booking)
    size_prices = {"small": 100, "medium": 150, "large": 200, "extra_large": 250}

    return size_prices.get(size, 100)


def generate_location_code(db: Session, name: str) -> str:
    """Generate a unique location code based on location name"""
    from apps.lockers.crud import get_locker_location_by_code

    # Take first 3 characters of name, convert to uppercase, remove spaces
    base_code = "".join(name.replace(" ", "").upper()[:3])
    if len(base_code) < 3:
        base_code = base_code.ljust(3, "X")

    # Try the base code first
    counter = 1
    code = f"{base_code}_{counter:03d}"

    # Keep incrementing until we find a unique code
    while get_locker_location_by_code(db, code):
        counter += 1
        code = f"{base_code}_{counter:03d}"
        if counter > 999:  # Safety check
            # Fallback to random code if too many locations with same prefix
            random_suffix = "".join(secrets.choice(string.digits) for _ in range(3))
            code = f"{base_code}_{random_suffix}"
            break

    return code


def build_locker_location_response(db: Session, location) -> LockerLocationRead:
    """Build LockerLocationRead response with shops populated"""
    response_data = LockerLocationRead.model_validate(location, from_attributes=True)
    from apps.lockers.models.shop_locker_association import ShopLockerAssociation
    from apps.shops.models.shops import Shop

    # Get associated shops with their details
    shop_associations = db.exec(
        select(Shop)
        .join(ShopLockerAssociation)
        .where(ShopLockerAssociation.locker_location_id == location.id)
    ).all()

    # Convert to ShopMinimalRead format
    response_data.shops = [
        ShopMinimalRead.model_validate(shop, from_attributes=True)
        for shop in shop_associations
    ]

    return response_data


def build_locker_location_with_units_response(
    db: Session, location, user_location: Optional[str] = None
) -> LockerLocationWithUnits:
    """Build LockerLocationWithUnits response with shops and all units populated"""
    from apps.core.utils import get_distance
    from apps.lockers.crud import get_locker_units
    from apps.lockers.models.shop_locker_association import ShopLockerAssociation
    from apps.shops.models.shops import Shop

    response_data = LockerLocationWithUnits.model_validate(
        location, from_attributes=True
    )

    # Get associated shops with their details
    shop_associations = db.exec(
        select(Shop)
        .join(ShopLockerAssociation)
        .where(ShopLockerAssociation.locker_location_id == location.id)
    ).all()

    # Convert to ShopMinimalRead format
    response_data.shops = [
        ShopMinimalRead.model_validate(shop, from_attributes=True)
        for shop in shop_associations
    ]

    # Get all units for this location
    units, _ = get_locker_units(
        db, location_id=location.id, limit=1000
    )  # Get all units
    response_data.units = [
        LockerUnitRead.model_validate(unit, from_attributes=True) for unit in units
    ]

    # Calculate number_of_columns as max(column_index) across all units
    col_indices = [u.column_index for u in units if u.column_index is not None]
    response_data.number_of_columns = max(col_indices) if col_indices else None

    # Calculate distance if user_location is provided
    if user_location and not "None" in user_location and location.position:
        response_data.distance = get_distance(user_location, location.position)
    else:
        response_data.distance = None

    return response_data


def create_reservation_read_with_qr_code(
    reservation: Optional[LockerReservation],
) -> Optional[LockerReservationRead]:
    """Helper function to create LockerReservationRead with qr_code_url populated"""
    if not reservation:
        return None

    # Create the base schema
    reservation_read = LockerReservationRead.model_validate(
        reservation, from_attributes=True
    )

    # Explicitly set the qr_code_url by calling the property
    reservation_read.qr_code_url = reservation.qr_code_url
    # Load description from locker location if available
    if reservation.unit and reservation.unit.location:
        reservation_read.description = reservation.unit.location.description  # type: ignore

    return reservation_read


# ===== Reservation Update Helper Functions =====
def update_unit_status_from_reservation(db: Session, reservation, new_status: str):
    """Update locker unit status based on reservation status"""

    from .tasks import sync_location_to_firebase_task

    if not reservation.locker_unit_id:
        return

    update_locker_unit(db, reservation.locker_unit_id, {"status": "OCCUPIED"})
    sync_location_to_firebase_task.delay(reservation.locker_unit_id, is_unit_id=True)


def handle_combo_activation(db: Session, reservation, reservation_id: str):
    """Handle combo status update when reservation becomes active"""
    if not reservation.combo_id:
        return

    from apps.products.crud import get_combo_by_id, update_combo
    from apps.products.tasks import sync_combo_to_firebase_task
    from apps.products.utils import parse_sales_duration_to_seconds

    combo = get_combo_by_id(db, reservation.combo_id)
    if not combo:
        return

    # Update combo timing if item is deposited and has sales duration
    if reservation.item_deposited_at and combo.sales_duration:
        duration_seconds = parse_sales_duration_to_seconds(combo.sales_duration)
        end_time = reservation.item_deposited_at + timedelta(seconds=duration_seconds)

        combo.status = COMBO_STATUS_SELLING
        combo.listing_end_date = end_time

        update_locker_reservation(db, reservation_id, {"sale_end_time": end_time})
        update_combo(db, combo)

        # Update Firebase shop combo count
        combo_count = count_shop_pending_combos(db, combo.shop_id)
        sync_shop_combo_count_to_firebase(combo.shop_id, combo_count)

    # Sync combo to Firebase
    sync_combo_to_firebase_task.delay(str(combo.id))
