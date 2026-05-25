"""Service layer for admin sales management APIs."""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlmodel import Session

from apps.core.constants import (
    COMBO_STATUS_EXPIRED,
    COMBO_STATUS_SELLING,
    COMBO_STATUS_SOLD,
    ORDER_STATUS_PICKED_UP,
    ORDER_STATUS_READY_FOR_PICKUP,
    ORDER_STATUS_REFUNDED,
    REVENUE_COUNTABLE_ORDER_STATUSES,
)
from apps.lockers.crud import get_locker_locations
from apps.lockers.models.reservation import LockerReservation
from apps.orders.models.orders import Order
from apps.products.models.combos import Combo
from apps.sales_management.services import (
    _calculate_food_loss_for_combos,
    _calculate_food_loss_reduction,
)
from apps.shops import crud as shops_crud
from apps.users.models.users import User

from . import crud, schemas
from .constants import (
    PRODUCT_STATUS_EXPIRED,
    PRODUCT_STATUS_SELLING,
    PRODUCT_STATUS_SELLING_DONATION_PHASE,
    PRODUCT_STATUS_SOLD_DONATION,
    PRODUCT_STATUS_SOLD_PICKED_UP,
    PRODUCT_STATUS_SOLD_READY_FOR_PICK_UP,
    VALID_PRODUCT_STATUSES,
)
from .exceptions import (
    access_denied_to_locker_locations,
    access_denied_to_shops,
    invalid_date_range,
    invalid_product_status,
)


def convert_utc_to_jst(utc_datetime: Optional[datetime]) -> Optional[datetime]:
    """
    Convert UTC datetime to JST (UTC+9) by adding 9 hours.

    Args:
        utc_datetime: UTC datetime (timezone-naive, stored in database as UTC)

    Returns:
        JST datetime (timezone-naive) or None if input is None
    """
    if utc_datetime is None:
        return None
    return utc_datetime + timedelta(hours=9)


def convert_jst_to_utc_range(
    start_date_jst: datetime, end_date_jst: datetime
) -> tuple[datetime, datetime]:
    """
    Convert JST date range to UTC date range for database filtering.

    If start_date = 2025-11-10 and end_date = 2025-11-20 in JST,
    this converts to UTC range:
    - Start: 2025-11-10 00:00:00 JST = 2025-11-09 15:00:00 UTC
    - End: 2025-11-20 23:59:59 JST = 2025-11-20 14:59:59 UTC

    If start_date = end_date = 2025-11-20 in JST:
    - Start: 2025-11-20 00:00:00 JST = 2025-11-19 15:00:00 UTC
    - End: 2025-11-20 23:59:59 JST = 2025-11-20 14:59:59 UTC

    Args:
        start_date_jst: Start date in JST (timezone-naive, treated as JST)
        end_date_jst: End date in JST (timezone-naive, treated as JST)

    Returns:
        Tuple of (start_datetime_utc, end_datetime_utc) as timezone-naive UTC datetimes
    """
    # Create JST timezone (UTC+9)
    jst = timezone(timedelta(hours=9))

    # Ensure start_date is beginning of day in JST
    if (
        start_date_jst.hour == 0
        and start_date_jst.minute == 0
        and start_date_jst.second == 0
    ):
        start_datetime_jst = start_date_jst.replace(tzinfo=jst)
    else:
        start_datetime_jst = start_date_jst.replace(
            hour=0, minute=0, second=0, microsecond=0, tzinfo=jst
        )

    # Ensure end_date is end of day in JST (23:59:59.999999)
    if end_date_jst.hour == 0 and end_date_jst.minute == 0 and end_date_jst.second == 0:
        end_datetime_jst = end_date_jst.replace(
            hour=23, minute=59, second=59, microsecond=999999, tzinfo=jst
        )
    else:
        end_datetime_jst = end_date_jst.replace(
            hour=23, minute=59, second=59, microsecond=999999, tzinfo=jst
        )

    # Convert to UTC and remove timezone info (database uses naive UTC)
    start_datetime_utc = start_datetime_jst.astimezone(timezone.utc).replace(
        tzinfo=None
    )
    end_datetime_utc = end_datetime_jst.astimezone(timezone.utc).replace(tzinfo=None)

    return start_datetime_utc, end_datetime_utc


def calculate_combo_status(
    combo: Combo, order: Optional[Order], reservation: Optional[LockerReservation]
) -> str:
    """
    Calculate the status for a combo based on combo status, order, and reservation.

    Status calculation logic:
    1. SELLING: Combo.status == COMBO_STATUS_SELLING and Combo.is_free = False
    2. SELLING_DONATION_PHASE: Combo.status == COMBO_STATUS_SELLING and Combo.is_free = True
    3. SOLD_DONATION: Combo.status == COMBO_STATUS_SOLD and Order.final_price == 0 and Order.status = ORDER_STATUS_PICKED_UP
    4. SOLD_PICKED_UP: Combo.status == COMBO_STATUS_SOLD and Order.status == ORDER_STATUS_PICKED_UP and (Combo.isfree=False or(is_free = True and Order.final_price !=0))
    5. SOLD_READY_FOR_PICK_UP: Combo.status == COMBO_STATUS_SOLD and Order.status == ORDER_STATUS_READY_FOR_PICKUP
    6. EXPIRED: Order.status == ORDER_STATUS_READY_FOR_PICKUP and pickup_deadline < current_time

    Args:
        combo: Combo object
        order: Optional Order object
        reservation: Optional LockerReservation object

    Returns:
        Status string matching PRODUCT_STATUS constants
    """
    # Check for EXPIRED status first (has priority)
    if combo.status == COMBO_STATUS_EXPIRED:
        return PRODUCT_STATUS_EXPIRED

    # Check for SOLD statuses
    if combo.status == COMBO_STATUS_SOLD:
        if order:
            # SOLD_DONATION: final_price == 0 and order.status == PICKED_UP (has priority)
            if order.final_price == 0 and order.status == ORDER_STATUS_PICKED_UP:
                return PRODUCT_STATUS_SOLD_DONATION
            # SOLD_PICKED_UP: order status is PICKED_UP
            elif order.status == ORDER_STATUS_PICKED_UP:
                return PRODUCT_STATUS_SOLD_PICKED_UP
            # SOLD_READY_FOR_PICK_UP: order status is READY_FOR_PICKUP
            elif order.status == ORDER_STATUS_READY_FOR_PICKUP:
                return PRODUCT_STATUS_SOLD_READY_FOR_PICK_UP
        # If combo is SOLD but no order, default to SOLD_READY_FOR_PICK_UP
        return PRODUCT_STATUS_SOLD_READY_FOR_PICK_UP

    # Check for SELLING statuses
    if combo.status == COMBO_STATUS_SELLING:
        # Check if in donation phase
        if combo.is_free:
            return PRODUCT_STATUS_SELLING_DONATION_PHASE
        else:
            return PRODUCT_STATUS_SELLING

    # Default fallback (should not happen for valid combos)
    return PRODUCT_STATUS_SELLING


def _process_combos_for_dashboard(
    combos_data: Dict[str, Dict],
    product_status: Optional[str],
) -> List[schemas.DashboardComboData]:
    """
    Process combos data: filter by status, calculate status, convert datetime, format to DashboardComboData.

    This function handles all business logic for processing combo data:
    - Filter by product_status (for SELLING_DONATION_PHASE and EXPIRED)
    - Calculate status for each combo
    - Convert datetime fields from UTC to JST
    - Format to DashboardComboData schema

    Args:
        combos_data: Dictionary mapping combo_id to dict containing combo, order, reservation, etc.
        product_status: Optional product status for filtering

    Returns:
        List of DashboardComboData objects
    """
    from apps.core.constants import (
        ORDER_STATUS_PICKED_UP,
        ORDER_STATUS_READY_FOR_PICKUP,
    )

    # Attach related data to combos for filtering
    for combo_id, data in combos_data.items():
        combo = data["combo"]
        if data["reservation"]:
            combo._reservation = data["reservation"]
        if data["order"]:
            combo._order = data["order"]

    # Filter in Python for special product_status (SELLING_DONATION_PHASE, EXPIRED)
    # These statuses require Python-based filtering as they depend on time-based calculations
    # We use calculate_combo_status() for consistency - the same function is used to
    # calculate the status field in the response, ensuring request filtering and response
    # status calculation use identical logic
    if product_status in [
        PRODUCT_STATUS_SELLING_DONATION_PHASE,
        PRODUCT_STATUS_EXPIRED,
    ]:
        filtered_combo_ids = set()
        for combo_id, data in combos_data.items():
            combo = data["combo"]
            order = data["order"]
            reservation = data["reservation"]
            calculated_status = calculate_combo_status(combo, order, reservation)
            if calculated_status == product_status:
                filtered_combo_ids.add(combo_id)

        filtered_data = {
            combo_id: data
            for combo_id, data in combos_data.items()
            if combo_id in filtered_combo_ids
        }
    else:
        filtered_data = combos_data

    # Format to DashboardComboData (excluding foodloss, co2_reduced, sale_price)
    dashboard_combo_data_list = []
    for combo_id, data in filtered_data.items():
        combo = data["combo"]
        order = data["order"]
        reservation = data["reservation"]
        locker_unit = data["locker_unit"]
        locker_location = data["locker_location"]
        user = data["user"]
        shop = data["shop"]

        # Get completed_at (for orders with status PICKED_UP or READY_FOR_PICKUP)
        completed_at = None
        if order and order.status in REVENUE_COUNTABLE_ORDER_STATUSES and order.status != ORDER_STATUS_REFUNDED:
            completed_at = order.completed_at

        # Calculate status based on combo, order, and reservation
        calculated_status = calculate_combo_status(combo, order, reservation)

        # Convert all datetime fields from UTC to JST for response
        item_deposit_at_jst = convert_utc_to_jst(
            reservation.item_deposited_at if reservation else None
        )
        sale_end_time_jst = convert_utc_to_jst(
            reservation.sale_end_time if reservation else None
        )
        completed_at_jst = convert_utc_to_jst(completed_at)
        picked_up_at_jst = convert_utc_to_jst(order.picked_up_at if order else None)

        dashboard_combo_data = schemas.DashboardComboData(
            id=combo.id,
            product_number=combo.product_number,
            combo_name=combo.name,
            combo_status=combo.status,
            status=calculated_status,
            is_free=combo.is_free,
            discount_percentage=combo.discount_percentage,
            original_price=combo.original_price,
            order_status=order.status if order else None,
            foodloss=0.0,  # Will be calculated in service
            co2_reduced=0.0,  # Will be calculated in service
            sale_duration=combo.sales_duration,
            item_deposit_at=item_deposit_at_jst,
            sale_end_time=sale_end_time_jst,
            locker_unit_id=locker_unit.id if locker_unit else None,
            unit_number=locker_unit.unit_number if locker_unit else None,
            locker_name=locker_location.name if locker_location else None,
            user_name=user.name if user else None,
            user_email=user.email if user else None,
            user_phone=user.phone if user else None,
            shop_name=shop.name if shop else None,
            sale_price=None,  # Will be calculated in service
            final_price=order.final_price if order else None,
            completed_at=completed_at_jst,
            picked_up_at=picked_up_at_jst,
        )
        dashboard_combo_data_list.append(dashboard_combo_data)

    return dashboard_combo_data_list


def get_dashboard_service(
    db: Session,
    user: User,
    search_text: Optional[str] = None,
    shop_ids: Optional[List[str]] = None,
    locker_location_ids: Optional[List[str]] = None,
    product_status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 20,
    offset: int = 0,
) -> schemas.DashboardResponse:

    validate_product_status(product_status)
    if (start_date is None) != (end_date is None):
        raise invalid_date_range()

    # 1. Access control
    accessible_shops = get_accessible_shops_service(db, user)
    accessible_shop_ids = {s.id for s in accessible_shops}

    if shop_ids:
        invalid = set(shop_ids) - accessible_shop_ids
        if invalid:
            raise access_denied_to_shops(invalid)
        filtered_shop_ids = shop_ids
    else:
        filtered_shop_ids = list(accessible_shop_ids)

    if not filtered_shop_ids:
        return _empty_dashboard(limit, offset)

    accessible_location_ids = _resolve_accessible_locations(
        db, user, locker_location_ids
    )

    # 2. Query combos
    # Trim search_text to remove leading/trailing whitespace
    trimmed_search_text = search_text.strip() if search_text else None
    # Set to None if empty string after trim
    if trimmed_search_text == "":
        trimmed_search_text = None

    # Convert JST dates to UTC for database filtering
    start_date_utc = None
    end_date_utc = None
    if start_date and end_date:
        start_date_utc, end_date_utc = convert_jst_to_utc_range(start_date, end_date)

    # Get raw combo data from database
    combos_data = crud.get_combos_with_filters(
        db=db,
        filtered_shop_ids=filtered_shop_ids,
        accessible_location_ids=accessible_location_ids,
        search_text=trimmed_search_text,
        start_date_utc=start_date_utc,
        end_date_utc=end_date_utc,
        product_status=product_status,
    )

    # 3. Process combos: filter by status, calculate status, format to DashboardComboData
    processed_combos = _process_combos_for_dashboard(combos_data, product_status)

    total = len(processed_combos)
    paginated = processed_combos[offset : offset + limit]

    # 4. Static metrics
    combo_ids = [c.id for c in processed_combos]
    orm_combos = crud.get_combos_by_ids(db, combo_ids)

    static_data = _calculate_static_data(db, combo_ids, orm_combos)

    # 5. Calculated fields for combo list (batch foodloss)
    enriched = _add_calculated_fields(db, paginated)

    return schemas.DashboardResponse(
        limit=limit,
        offset=offset,
        total=total,
        static_data=static_data,
        combo_data=enriched,
    )


def validate_product_status(product_status: Optional[str]) -> None:
    """Validate product_status parameter."""
    if product_status is not None and product_status not in VALID_PRODUCT_STATUSES:
        raise invalid_product_status(product_status, VALID_PRODUCT_STATUSES)


def get_accessible_shops_service(db: Session, user) -> list[schemas.AccessibleShop]:

    if user.role == "admin":
        shops = shops_crud.get_all_active_shops(db)
    elif user.role == "owner_locker":
        shops = shops_crud.get_shops_by_locker_owner(db, user.id)

    return [
        schemas.AccessibleShop.model_validate(shop, from_attributes=True)
        for shop in shops
    ]


def _calculate_static_data(
    db: Session,
    combo_ids: List[str],
    combos: List[Combo],
) -> schemas.DashboardStaticData:

    orders = crud.get_orders_by_combo_ids(db, combo_ids, status=ORDER_STATUS_PICKED_UP)

    sales = 0.0
    sold_non_donated = sold_donated = unsold = 0
    sold_combos = []

    for combo in combos:
        if combo.status == COMBO_STATUS_SOLD:
            order = orders.get(combo.id)
            if order:
                final_price = order.final_price or 0.0
                sales += final_price
                if final_price == 0:
                    sold_donated += 1
                else:
                    sold_non_donated += 1
                sold_combos.append(combo)

        elif combo.status == COMBO_STATUS_EXPIRED:
            unsold += 1

    foodloss_total = _calculate_food_loss_reduction(db, sold_combos)
    co2 = round(foodloss_total * 2.5 / 1000)

    return schemas.DashboardStaticData(
        total_sales_revenue=str(sales),
        total_foodloss_reduced=str(foodloss_total),
        total_co2_reduced=str(co2),
        total_sold_products_non_donated=str(sold_non_donated),
        total_sold_products_donated=str(sold_donated),
        total_unsold_products=str(unsold),
    )


def _resolve_accessible_locations(
    db: Session, user: User, request_ids: Optional[List[str]]
):
    if user.role == "admin":
        if not request_ids:
            return None
        locations = crud.get_locker_locations_by_ids(db, request_ids)
        return [loc.id for loc in locations]

    # owner_locker
    user_locations, _ = get_locker_locations(
        db, owner_id=user.id, is_active=True, limit=None, offset=0
    )
    user_location_ids = {l.id for l in user_locations}

    if request_ids:
        invalid = set(request_ids) - user_location_ids
        if invalid:
            raise access_denied_to_locker_locations(invalid)
        return request_ids

    return list(user_location_ids)


def _add_calculated_fields(
    db: Session,
    combo_data_list: List[schemas.DashboardComboData],
) -> List[schemas.DashboardComboData]:

    if not combo_data_list:
        return []

    ids = [c.id for c in combo_data_list]
    combos = crud.get_combos_by_ids(db, ids)
    combos_by_id = {c.id: c for c in combos}

    foodloss_map = _calculate_food_loss_reduction_map(db, combos)

    for item in combo_data_list:
        combos_by_id.get(item.id)
        fl = foodloss_map.get(item.id, 0)

        item.sale_price = (
            round((100 - item.discount_percentage) * item.original_price / 100)
            if item.discount_percentage and item.original_price
            else None
        )
        item.foodloss = fl
        item.co2_reduced = fl * 2.5 / 1000

    return combo_data_list


def _calculate_food_loss_reduction_map(db: Session, combos: List[Combo]):
    """
    Calculate food loss reduction map for all combos (regardless of status).
    Returns a dictionary mapping combo_id to food loss in grams (as float).

    Args:
        db: Database session
        combos: List of combo objects (any status)

    Returns:
        Dictionary mapping combo_id to food loss value (float)
    """
    if not combos:
        return {}

    result = {}
    for combo in combos:
        # Calculate food loss for this combo regardless of status
        food_loss = _calculate_food_loss_for_combos(db, [combo])
        result[combo.id] = float(food_loss)
    return result


def _empty_dashboard(limit: int, offset: int):
    return schemas.DashboardResponse(
        limit=limit,
        offset=offset,
        total=0,
        static_data=schemas.DashboardStaticData(
            total_sales_revenue="0.0",
            total_foodloss_reduced="0",
            total_co2_reduced="0.0",
            total_sold_products_non_donated="0",
            total_sold_products_donated="0",
            total_unsold_products="0",
        ),
        combo_data=[],
    )


def get_combo_matching_stats_service(
    db: Session,
    start_date: datetime,
    end_date: datetime,
    locker_ids: List[str],
    include_support_combos: bool = True,
    include_nonsupport_combos: bool = True,
) -> schemas.ComboMatchingStatsResponse:
    """
    Get combo matching statistics by locker and date.

    Returns a table structure where:
    - Dates list: all dates from start_date to end_date
    - Lockers: list of lockers with counts by date
    """
    from sqlmodel import select

    from apps.lockers.models.unit import LockerUnit

    # Validate date range
    if start_date > end_date:
        raise invalid_date_range()

    # Validate locker_ids
    if not locker_ids:
        return schemas.ComboMatchingStatsResponse(dates=[], lockers=[])

    # Build date list (YYYY-MM-DD format)
    dates = []
    current_date = start_date.date()
    end_date_only = end_date.date()
    while current_date <= end_date_only:
        dates.append(current_date.strftime("%Y-%m-%d"))
        current_date += timedelta(days=1)

    # Get locker locations info
    locker_locations = crud.get_locker_locations_by_ids(db, locker_ids)
    locker_map = {loc.id: loc.name for loc in locker_locations}

    # Get locker unit IDs for the specified locker locations
    locker_units = db.exec(
        select(LockerUnit.id, LockerUnit.location_id).where(
            LockerUnit.location_id.in_(locker_ids)
        )
    ).all()
    locker_unit_ids = [unit.id for unit in locker_units]

    # If no locker units found, return empty result
    if not locker_unit_ids:
        return schemas.ComboMatchingStatsResponse(dates=dates, lockers=[])

    # Get query results from CRUD
    results = crud.get_combo_matching_stats_by_date_and_locker(
        db=db,
        start_date=start_date,
        end_date=end_date,
        locker_unit_ids=locker_unit_ids,
        include_support_combos=include_support_combos,
        include_nonsupport_combos=include_nonsupport_combos,
    )

    # Build result structure with all dates initialized to 0
    locker_stats = {}
    for locker_id in locker_ids:
        locker_stats[locker_id] = {date: 0 for date in dates}

    # Fill in actual counts from query results
    for result in results:
        locker_id = result.location_id
        date_str = result.order_date.strftime("%Y-%m-%d")
        count = result.count

        if locker_id in locker_stats and date_str in locker_stats[locker_id]:
            locker_stats[locker_id][date_str] = count

    # Format response
    lockers = []
    for locker_id in locker_ids:
        locker_name = locker_map.get(locker_id, f"Locker {locker_id}")
        lockers.append(
            {
                "id": locker_id,
                "name": locker_name,
                "counts_by_date": locker_stats.get(locker_id, {}),
            }
        )

    return schemas.ComboMatchingStatsResponse(dates=dates, lockers=lockers)
