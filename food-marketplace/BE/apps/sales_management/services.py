"""
Sales Management Services

Business logic for sales management functionality including dashboard analytics,
unsold/sold item management, and data formatting for UI display.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from sqlmodel import Session

from apps.core.constants import (
    COMBO_STATUS_PREPARATION_TO_LOCKER,
    COMBO_STATUS_SOLD,
    ORDER_STATUS_PICKED_UP,
    ORDER_STATUS_REFUNDED,
    REVENUE_COUNTABLE_ORDER_STATUSES,
)
from apps.core.utils import get_current_time
from apps.products.crud import get_combo_with_product_masters
from apps.products.models.combos import Combo

from . import crud, schemas
from .exceptions import both_values_provided
from .utils import get_info_display_info, has_picked_up_orders
from .validators import validate_date_range, validate_shop_access


def _convert_jst_date_to_utc_range(date_jst: datetime) -> tuple[datetime, datetime]:
    """
    Convert a JST date to UTC date range for database queries.

    Args:
        date_jst: A datetime object representing a date in JST (UTC+9)

    Returns:
        Tuple of (start_of_day_utc, end_of_day_utc) as naive datetime objects
    """
    # Create UTC+9 timezone
    jst = timezone(timedelta(hours=9))

    # Create start/end of day in JST
    start_of_day_jst = datetime.combine(date_jst.date(), datetime.min.time()).replace(
        tzinfo=jst
    )
    end_of_day_jst = datetime.combine(date_jst.date(), datetime.max.time()).replace(
        tzinfo=jst
    )

    # Convert to UTC and remove timezone info (database uses naive UTC)
    start_of_day_utc = start_of_day_jst.astimezone(timezone.utc).replace(tzinfo=None)
    end_of_day_utc = end_of_day_jst.astimezone(timezone.utc).replace(tzinfo=None)

    return start_of_day_utc, end_of_day_utc


def get_sales_dashboard_service(
    db: Session,
    user,
    month: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    product_number: Optional[str] = None,
    name: Optional[str] = None,
    locker_name: Optional[str] = None,
) -> schemas.SalesDashboard:
    """
    Get sales dashboard data following sold_spec.md requirements.
    """
    # Validate shop access
    shop_id = validate_shop_access(user)

    # Validate time input
    if month and (start_date or end_date):
        raise both_values_provided()

    # Calculate date range for the month or for start_date, end_date if provided
    if month:
        year, month_num = month.split("-")
        start_date_for_combos = datetime(int(year), int(month_num), 1)
        # Calculate end of month
        if start_date_for_combos.month == 12:
            end_date_for_combos = datetime(start_date_for_combos.year + 1, 1, 1)
        else:
            end_date_for_combos = datetime(
                start_date_for_combos.year, start_date_for_combos.month + 1, 1
            )
    else:
        if start_date and end_date:
            start_date_for_combos = start_date
            end_date_for_combos = end_date
        else:
            now = get_current_time()
            start_date_for_combos = datetime(now.year, now.month, 1)
            # Calculate end of month
            if start_date_for_combos.month == 12:
                end_date_for_combos = datetime(start_date_for_combos.year + 1, 1, 1)
            else:
                end_date_for_combos = datetime(
                    start_date_for_combos.year, start_date_for_combos.month + 1, 1
                )

    # Get combos for range start_date and end_date
    current_combos = crud.get_shop_combos_by_date_range(
        db,
        shop_id,
        start_date_for_combos,
        end_date_for_combos,
        product_number,
        name,
        locker_name,
    )

    # Calculate food loss this month and last month reduction using actual product master weights
    food_loss_this_month, food_loss_last_month = _get_foodloss_current_and_last_month(
        db, shop_id
    )

    # Calculate metrics for current month
    # Helper function to check if combo has picked up orders
    # Split combos into categories efficiently
    sold_combos = []
    unsold_combos = []

    for combo in current_combos:
        if combo.status == COMBO_STATUS_SOLD and has_picked_up_orders(combo):
            sold_combos.append(combo)
        else:
            unsold_combos.append(combo)

    # Filter donations from sold combos (they already have picked up orders)
    donation_combos = [combo for combo in sold_combos if combo.is_free]

    # Calculate revenue (excluding donations)
    # Get only the successful/completed order for each sold combo
    total_revenue = 0
    for combo in sold_combos:
        # Find the completed order for this combo (should be only one)
        completed_order = next(
            (order for order in combo.orders if order.status == ORDER_STATUS_PICKED_UP),
            None,
        )
        if completed_order:
            total_revenue += completed_order.final_price or 0

    # Calculate status distribution
    status_counts = {}
    for combo in current_combos:
        status_counts[combo.status] = status_counts.get(combo.status, 0) + 1

    # Calculate recent activity metrics
    recent_sales_count = crud.get_recent_sales_count(db, shop_id, hours=24)
    pending_placement_count = crud.get_pending_placement_count(db, shop_id)
    expiring_soon_count = crud.get_expiring_soon_count(db, shop_id, hours=2)

    return schemas.SalesDashboard(
        # Food Loss Banner (Section 2 of sold_spec.md)
        food_loss_this_month_grams=food_loss_this_month,
        food_loss_last_month_grams=food_loss_last_month,
        # Monthly Support and Revenue (Section 5 of sold_spec.md)
        support_count_this_month=len(sold_combos),  # 今月支援
        total_revenue_this_month=total_revenue,
        # Additional metrics
        unsold_count_this_month=len(unsold_combos),
        sold_count_this_month=len(sold_combos),
        donation_count_this_month=len(donation_combos),
        status_counts=status_counts,
        recent_sales_count=recent_sales_count,
        pending_placement_count=pending_placement_count,
        expiring_soon_count=expiring_soon_count,
    )


def _get_foodloss_current_and_last_month(db: Session, shop_id: str):
    now = get_current_time()
    current_month_start = datetime(now.year, now.month, 1)
    current_month_end = datetime(now.year, now.month, now.day)

    if now.month == 1:
        last_month_start = datetime(now.year - 1, 12, 1)
        last_month_end = datetime(now.year, 1, 1)
    else:
        last_month_start = datetime(now.year, now.month - 1, 1)
        last_month_end = datetime(now.year, now.month, 1)

    last_month_combos = crud.get_shop_combos_by_date_range(
        db, shop_id, last_month_start, last_month_end
    )
    current_month_combos = crud.get_shop_combos_by_date_range(
        db, shop_id, current_month_start, current_month_end
    )
    food_loss_this_month = _calculate_food_loss_reduction(db, current_month_combos)
    food_loss_last_month = _calculate_food_loss_reduction(db, last_month_combos)

    return food_loss_last_month, food_loss_this_month


def _calculate_food_loss_for_combos(db: Session, combos: List[Combo]) -> float:
    """
    Helper function to calculate food loss reduction in grams for any combos (regardless of status).
    Calculates the actual food waste weight from product masters in each combo.

    Args:
        db: Database session for loading product relationships
        combos: List of combo objects (any status)

    Returns:
        Total food waste saved in grams (as float)
    """
    if not combos:
        return 0.0

    total_food_waste_saved = 0.0
    for combo in combos:
        # Get combo with loaded product relationships
        full_combo = get_combo_with_product_masters(db, combo.id)
        if not full_combo or not full_combo.combo_products:
            continue

        combo_food_waste = 0.0
        for combo_product in full_combo.combo_products:
            if (
                combo_product.product_master
                and hasattr(combo_product.product_master, "food_waste_weight")
                and combo_product.product_master.food_waste_weight
            ):
                # Multiply by quantity to get total weight for this product
                product_waste = (
                    combo_product.product_master.food_waste_weight
                    * combo_product.quantity
                )
                combo_food_waste += product_waste

        total_food_waste_saved += combo_food_waste

    return total_food_waste_saved


def _calculate_food_loss_reduction(db: Session, combos: List[Combo]) -> int:
    """
    Calculate food loss reduction in grams for sold items only.
    Filters combos to only those with picked up orders, then calculates food waste.

    Args:
        combos: List of combo objects
        db: Database session for loading product relationships

    Returns:
        Total food waste saved in grams (as int, for sold items only)
    """
    combo_has_picked_up = []
    for combo in combos:
        if combo.orders and combo.orders[0].status == ORDER_STATUS_PICKED_UP:
            combo_has_picked_up.append(combo)

    if not combo_has_picked_up:
        return 0

    total_food_waste_saved = _calculate_food_loss_for_combos(db, combo_has_picked_up)
    return int(total_food_waste_saved)


def get_unsold_items_service(
    db: Session,
    user,
    limit: int = 20,
    offset: int = 0,
    search: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    product_number: Optional[str] = None,
    name: Optional[str] = None,
    locker_name: Optional[str] = None,
) -> Tuple[List[schemas.SalesComboItem], int]:
    """
    Get list of unsold items with formatting for UI display.
    Returns tuple of (items, total_count) following your project pattern.

    Note: start_date and end_date are expected to be in JST (UTC+9) from the API
    """
    # Validate inputs
    shop_id = validate_shop_access(user)

    # Convert JST dates to UTC for database queries
    start_date_utc = None
    end_date_utc = None

    if start_date:
        start_date_utc, _ = _convert_jst_date_to_utc_range(start_date)
    if end_date:
        _, end_date_utc = _convert_jst_date_to_utc_range(end_date)

    # Get data using unified CRUD function with new search parameters
    combos, total = crud.get_shop_combos(
        db=db,
        shop_id=shop_id,
        limit=limit,
        offset=offset,
        search=search,
        start_date=start_date_utc,
        end_date=end_date_utc,
        product_number=product_number,
        name=name,
        locker_name=locker_name,
    )

    # Format items for display
    items = [_format_combo_for_display(combo, db) for combo in combos]

    return items, total


def get_sold_items_service(
    db: Session,
    user,
    limit: int = 20,
    offset: int = 0,
    search: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    product_number: Optional[str] = None,
    name: Optional[str] = None,
    locker_name: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> Tuple[List[schemas.SalesComboItem], int]:
    """
    Get list of sold items with purchase information.
    Returns tuple of (items, total_count) following your project pattern.

    Note: All date parameters are expected to be in JST (UTC+9) from the API
    """
    # Validate inputs
    shop_id = validate_shop_access(user)

    # Use new parameters if provided, otherwise fall back to legacy ones
    final_start_date = start_date or date_from
    final_end_date = end_date or date_to
    validate_date_range(final_start_date, final_end_date)

    # Convert JST dates to UTC for database queries
    start_date_utc = None
    end_date_utc = None

    if final_start_date:
        start_date_utc, _ = _convert_jst_date_to_utc_range(final_start_date)
    if final_end_date:
        _, end_date_utc = _convert_jst_date_to_utc_range(final_end_date)

    # Get data using unified CRUD function with search parameters
    combos, total = crud.get_shop_combos(
        db=db,
        shop_id=shop_id,
        limit=limit,
        offset=offset,
        search=search,
        start_date=start_date_utc,
        end_date=end_date_utc,
        product_number=product_number,
        name=name,
        locker_name=locker_name,
        status=COMBO_STATUS_SOLD,  # Only get sold items
    )

    # Format items for display
    items = [_format_combo_for_display(combo, db, is_sold=True) for combo in combos]

    return items, total


def _format_combo_for_display(
    combo, db: Session, is_sold: bool = False
) -> schemas.SalesComboItem:
    """
    Format a combo for display in the sales management UI.
    """
    # Get locker information using CRUD
    locker_info = _get_combo_locker_info(combo, db)

    # Get reservation for countdown calculations (if needed)
    reservation = None
    if combo.status == COMBO_STATUS_PREPARATION_TO_LOCKER:
        from apps.products.crud import get_combo_locker_reservation

        reservation = get_combo_locker_reservation(db, combo.id)

    # Get status display information with reservation context
    info_display = get_info_display_info(combo, reservation)

    return schemas.SalesComboItem(
        id=combo.id,
        name=combo.name,
        description=combo.description,
        product_code=combo.product_number,
        status=combo.status,
        order_status=combo.orders[0].status if combo.orders else None,
        original_price=combo.original_price,
        discount_price=combo.discount_price,
        final_price=combo.orders[0].final_price if combo.orders else None,
        discount_percentage=combo.discount_percentage,
        is_free=combo.is_free,
        created_at=combo.created_at,
        listing_end_date=combo.listing_end_date,
        placement_countdown_seconds=info_display.get("countdown_seconds"),
        placement_countdown_display=info_display.get("countdown_display"),
        locker_location_name=locker_info.get("location_name"),
        locker_unit_number=locker_info.get("unit_number"),
        locker_location_id=locker_info.get("location_id"),
        status_display_text=info_display.get("display_status_text", ""),
        display_time=info_display.get("display_time"),
        display_time_label=info_display.get("display_time_label"),
    )


def _get_combo_locker_info(combo, db: Session) -> dict:
    """
    Get locker information for a combo using CRUD.
    """
    try:
        result = crud.get_combo_with_locker_info(db, combo.id)
        if result and len(result) == 3:
            combo_obj, unit, location = result
            return {
                "location_name": location.name if location else "Unknown Location",
                "unit_number": unit.unit_number if unit else "Unknown Unit",
                "location_id": location.id if location else None,
            }
    except Exception:
        pass

    return {
        "location_name": "Unknown Location",
        "unit_number": "Unknown Unit",
        "location_id": None,
    }
