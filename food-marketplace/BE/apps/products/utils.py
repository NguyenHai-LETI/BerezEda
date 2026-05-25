"""
Utility functions for products module to reduce code duplication
"""

from datetime import timedelta
from typing import Optional

from sqlmodel import Session, and_, col, func, select

from apps.core.constants import (
    COMBO_STATUS_PREPARATION_TO_LOCKER,
    COMBO_STATUS_SELLING,
    COMBO_STATUS_SOLD,
    ORDER_STATUS_PICKED_UP,
    ORDER_STATUS_READY_FOR_PICKUP,
)
from apps.core.utils import get_current_time
from apps.products.crud import get_combo_locker_unit_with_location
from apps.products.models import Combo
from apps.products.schemas import LockerLocationBasic, LockerUnitRead, ShopMinimalRead
from apps.shops.crud import get_shop
from apps.users.models import User


def parse_sales_duration_to_seconds(sales_duration: str) -> int:
    """
    Parse sales_duration string (e.g., "2時間", "30分", "1時間30分") to seconds

    Args:
        sales_duration: Duration string in Japanese format

    Returns:
        int: Duration in seconds
    """
    total_minutes = 0

    if "時間" in sales_duration:
        hours_part = sales_duration.split("時間")[0]
        try:
            total_minutes += int(hours_part) * 60
        except:
            pass
        # Check for additional minutes after hours
        if "分" in sales_duration:
            remaining = (
                sales_duration.split("時間")[1]
                if "時間" in sales_duration
                else sales_duration
            )
            if remaining and "分" in remaining:
                minutes_part = remaining.replace("分", "").strip()
                try:
                    total_minutes += int(minutes_part)
                except:
                    pass
    elif "分" in sales_duration:
        minutes_part = sales_duration.replace("分", "").strip()
        try:
            total_minutes = int(minutes_part)
        except:
            pass

    return total_minutes * 60


def populate_combo_timing_fields(combo_data, combo: Combo):
    """
    Populate timing-related fields for combo response schemas

    Args:
        combo_data: The schema object to populate
        combo: The Combo model instance
    """
    now = get_current_time()
    if not combo.listing_end_date:
        return

    time_remaining = combo.listing_end_date - now

    # Calculate sales duration in seconds
    sales_duration_seconds = None
    if combo.sales_duration:
        sales_duration_seconds = parse_sales_duration_to_seconds(combo.sales_duration)

    if not sales_duration_seconds:
        return

    # Total seconds remaining until expiration
    combo_data.time_remaining_seconds = max(0, int(time_remaining.total_seconds()))

    two_thirds_duration = sales_duration_seconds * 2 / 3
    discount_phase_start = combo.listing_end_date - timedelta(
        seconds=(sales_duration_seconds - two_thirds_duration)
    )

    # Calculate next status change based on business logic
    if combo.status == COMBO_STATUS_SELLING:
        combo_data.next_status_change_at = discount_phase_start
    else:
        combo_data.next_status_change_at = None


def populate_combo_pricing_fields(
    combo_data, combo: Combo, user: Optional[User] = None
):
    """
    Populate pricing-related fields for combo response schemas

    Args:
        combo_data: The schema object to populate
        combo: The Combo model instance
        user: Optional user object for permission checks
    """
    from decimal import ROUND_HALF_UP, Decimal

    original_price = combo.original_price or 0
    combo_data.can_be_free = (
        combo.is_free
        and combo.status == COMBO_STATUS_SELLING
        and user is not None
        and (
            getattr(user, "is_verification_qrcode", False)
            or getattr(user, "my_portal", None) == "linked"
        )
    )  # Indicates if MyNa Portal users can get it free

    # Calculate discounted price (applies to all users when in discount phase)
    if combo.discount_percentage > 0:
        discount_amount = (original_price * combo.discount_percentage) / 100
        combo_data.discounted_price = int(
            Decimal(original_price - discount_amount).to_integral_value(ROUND_HALF_UP)
        )
    else:
        combo_data.discounted_price = original_price

    # Calculate current effective price based on status
    if combo.status == COMBO_STATUS_SELLING:
        combo_data.current_effective_price = original_price
    else:
        combo_data.current_effective_price = original_price
    combo_data.discounted_price = combo_data.discounted_price


def populate_combo_shop_info(combo_data, combo: Combo, db: Session):
    """
    Populate shop information for combo response schemas

    Args:
        combo_data: The schema object to populate
        combo: The Combo model instance
        db: Database session
    """
    # Only populate if shop data is not already set (to avoid overriding ShopBasicRead)
    if combo_data.shop is None:
        if combo.shop:
            combo_data.shop = ShopMinimalRead.model_validate(
                combo.shop, from_attributes=True
            )
        else:
            shop = get_shop(db, combo.shop_id)
            if shop:
                combo_data.shop = ShopMinimalRead.model_validate(
                    shop, from_attributes=True
                )


def populate_combo_locker_info(combo_data, combo: Combo, db: Session):
    """
    Populate locker information for combo response schemas

    Args:
        combo_data: The schema object to populate
        combo: The Combo model instance
        db: Database session
    """
    result = get_combo_locker_unit_with_location(db, combo.id)

    if result:
        unit, location, reservation = result
        # Create nested location object
        location_data = LockerLocationBasic.model_validate(
            location, from_attributes=True
        )
        from apps.core.constants import COMBO_STATUS_PREPARATION_TO_LOCKER

        locker_unit = LockerUnitRead(
            id=unit.id,
            unit_number=unit.unit_number,
            status=unit.status,
            size=unit.size,
            access_code=reservation.access_code if reservation else None,
            location=location_data,
            preparation_deadline=(
                reservation.preparation_deadline if reservation else None
            ),
            locker_reservation_id=reservation.id if reservation else None,
            qr_code_url=reservation.qr_code_url if reservation else None,
            is_qr_active=combo.status == COMBO_STATUS_PREPARATION_TO_LOCKER,
        )
        combo_data.locker_unit = locker_unit


def enrich_combo_with_calculated_fields(
    combo_data, combo: Combo, db: Session, user: Optional[User] = None
):
    """
    Enrich combo data with all calculated fields (timing, pricing, shop, locker)

    Args:
        combo_data: The schema object to populate
        combo: The Combo model instance
        db: Database session
    """
    # Add shop information
    populate_combo_shop_info(combo_data, combo, db)

    # Add locker information
    populate_combo_locker_info(combo_data, combo, db)

    # Set default distance
    combo_data.distance = 10.0  # Default test value

    # Calculate timing fields
    populate_combo_timing_fields(combo_data, combo)

    # Calculate pricing fields
    populate_combo_pricing_fields(combo_data, combo, user)


def count_shop_pending_combos(db: Session, shop_id: str) -> int:
    """
    Count combos for shop that are in locker reserved status.

    Criteria:
    - Not draft
    - Status is "locker_reserved"

    Args:
        db: Database session
        shop_id: Shop ID

    Returns:
        int: Count of pending combos
    """
    try:
        stmt = (
            select(func.count(col(Combo.id)))
            .select_from(Combo)
            .where(
                and_(
                    col(Combo.shop_id) == shop_id,
                    col(Combo.is_draft) == False,
                    col(Combo.status) == COMBO_STATUS_PREPARATION_TO_LOCKER,
                )
            )
        )

        result = db.exec(stmt).first()
        return result or 0

    except Exception as e:
        from apps.core.logging import logger

        logger.error(f"Error counting pending combos for shop {shop_id}: {e}")
        return 0


def sync_shop_combo_count_to_firebase(shop_id: str, combo_count: int):
    """
    Sync the pending combo count to Firebase shop document.

    Args:
        shop_id: ID of the shop
        combo_count: Number of pending combos
    """
    try:
        from apps.shops.tasks import update_shop_field_to_firebase_task

        # Update the pending_combo_count field in Firebase
        update_data = {"pending_combo_count": combo_count}

        update_shop_field_to_firebase_task.delay(shop_id, update_data)

    except Exception as e:
        from apps.core.logging import logger

        logger.error(f"Error triggering Firebase sync for shop {shop_id}: {e}")


def combo_sales_success(db: Session):
    """
    Return all combos that have been successfully sold.

    A combo is considered successfully sold when:
    - Combo status is SOLD
    - Associated order status is PICKED_UP

    Args:
        db: Database session

    Returns:
        List[Combo]: List of successfully sold combos
    """
    from apps.orders.models import Order

    # Query combos with SOLD status that have PICKED_UP orders
    statement = (
        select(Combo)
        .join(Order, col(Order.combo_id) == col(Combo.id))
        .where(
            and_(
                col(Combo.status) == COMBO_STATUS_SOLD,
                col(Order.status) == ORDER_STATUS_PICKED_UP,
            )
        )
        .distinct()
    )

    return db.exec(statement).all()


def combo_sales_pending(db: Session):
    """
    Return all combos that are pending sale completion.

    A combo is considered pending sale when:
    - Combo status is SOLD
    - Associated order status is not PICKED_UP

    Args:
        db: Database session

    Returns:
        List[Combo]: List of pending sale combos
    """
    from apps.orders.models import Order

    # Query only Combo IDs to avoid DISTINCT on JSON columns
    statement = (
        select(Combo.id)
        .join(Order, col(Order.combo_id) == col(Combo.id))
        .where(
            and_(
                col(Combo.status) == COMBO_STATUS_SOLD,
                col(Order.status) == ORDER_STATUS_READY_FOR_PICKUP,
            )
        )
    )
    combo_ids = [row[0] for row in db.exec(statement).all()]
    if not combo_ids:
        return []
    # Now fetch full Combo objects
    combos = db.exec(select(Combo).where(col(Combo.id).in_(combo_ids))).all()
    return combos
