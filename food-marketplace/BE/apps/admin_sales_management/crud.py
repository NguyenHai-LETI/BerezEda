"""CRUD operations for admin sales management module."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import and_, or_
from sqlmodel import Session, desc, select

from apps.core.constants import (
    COMBO_STATUS_EXPIRED,
    COMBO_STATUS_SELLING,
    COMBO_STATUS_SOLD,
    ORDER_STATUS_PICKED_UP,
    ORDER_STATUS_READY_FOR_PICKUP,
    ORDER_STATUS_REFUNDED,
    REVENUE_COUNTABLE_ORDER_STATUSES,
)
from apps.core.utils import get_current_time
from apps.lockers.models.location import LockerLocation
from apps.lockers.models.reservation import LockerReservation
from apps.lockers.models.unit import LockerUnit
from apps.orders.models.orders import Order
from apps.products.models.combos import Combo
from apps.products.utils import parse_sales_duration_to_seconds
from apps.shops.models.shops import Shop
from apps.users.models.users import User

from .constants import (
    PRODUCT_STATUS_EXPIRED,
    PRODUCT_STATUS_SELLING,
    PRODUCT_STATUS_SELLING_DONATION_PHASE,
    PRODUCT_STATUS_SOLD_DONATION,
    PRODUCT_STATUS_SOLD_PICKED_UP,
    PRODUCT_STATUS_SOLD_READY_FOR_PICK_UP,
)


def get_locker_locations_by_ids(
    db: Session, location_ids: List[str]
) -> List[LockerLocation]:
    """Get locker locations by IDs using batch query."""
    if not location_ids:
        return []
    return list(
        db.exec(select(LockerLocation).where(LockerLocation.id.in_(location_ids))).all()
    )


def get_combos_by_ids_ordered(db: Session, combo_ids: List[str]) -> List[Combo]:
    """Get combo objects by IDs, ordered by updated_at desc."""
    if not combo_ids:
        return []
    return list(
        db.exec(
            select(Combo)
            .where(Combo.id.in_(combo_ids))
            .order_by(desc(Combo.updated_at))
        ).all()
    )


def get_combos_with_filters(
    db: Session,
    filtered_shop_ids: List[str],
    accessible_location_ids: Optional[List[str]],
    search_text: Optional[str],
    start_date_utc: Optional[datetime],
    end_date_utc: Optional[datetime],
    product_status: Optional[str],
) -> Dict[str, Dict]:
    """
    Get combos with filters from database, ordered by updated_at desc.

    This function only handles database queries and returns raw data.
    Business logic (filtering, status calculation, formatting) is handled in services.

    Args:
        db: Database session
        filtered_shop_ids: List of shop IDs to filter by
        accessible_location_ids: Optional list of locker location IDs
        search_text: Optional search text for combo name or user name
        start_date_utc: Start date in UTC (already converted from JST)
        end_date_utc: End date in UTC (already converted from JST)
        product_status: Optional product status for SQL filtering

    Returns:
        Dictionary mapping combo_id to dict containing:
        - combo: Combo object
        - reservation: LockerReservation object (or None)
        - order: Order object (or None)
        - locker_unit: LockerUnit object (or None)
        - locker_location: LockerLocation object (or None)
        - user: User object (or None)
        - shop: Shop object (or None)
    """
    # Build base query with joins for filtering
    subquery = (
        select(Combo.id)
        .outerjoin(LockerReservation, LockerReservation.combo_id == Combo.id)
        .outerjoin(LockerUnit, LockerUnit.id == LockerReservation.locker_unit_id)
        .outerjoin(LockerLocation, LockerLocation.id == LockerUnit.location_id)
        .outerjoin(Order, Order.combo_id == Combo.id)
        .outerjoin(User, User.id == Order.user_id)
    )

    # Build conditions for base filters
    conditions = []

    # Filter combo status: only SELLING, SOLD, EXPIRED
    allowed_combo_statuses = [
        COMBO_STATUS_SELLING,
        COMBO_STATUS_SOLD,
        COMBO_STATUS_EXPIRED,
    ]
    conditions.append(Combo.status.in_(allowed_combo_statuses))

    # Filter by shop_ids (only if list is not empty)
    if filtered_shop_ids and len(filtered_shop_ids) > 0:
        conditions.append(Combo.shop_id.in_(filtered_shop_ids))

    # Filter by locker_location_ids (only if explicitly provided)
    if accessible_location_ids:
        conditions.append(LockerLocation.id.in_(accessible_location_ids))

    # Filter by search_text (combo name or user name)
    if search_text:
        search_condition = or_(
            Combo.name.ilike(f"%{search_text}%"),
            User.name.ilike(f"%{search_text}%"),
        )
        conditions.append(search_condition)

    # Filter by start_date and end_date (already in UTC)
    # If Combo.status = SOLD, filter by Order.completed_at
    # Otherwise, filter by Combo.updated_at
    if start_date_utc and end_date_utc:
        date_filter_conditions = or_(
            # For SOLD combos: filter by Order.completed_at
            and_(
                Combo.status == COMBO_STATUS_SOLD,
                Order.completed_at >= start_date_utc,
                Order.completed_at <= end_date_utc,
            ),
            # For other allowed statuses: filter by Combo.updated_at
            and_(
                Combo.status != COMBO_STATUS_SOLD,
                Combo.status.in_(allowed_combo_statuses),
                Combo.updated_at >= start_date_utc,
                Combo.updated_at <= end_date_utc,
            ),
        )
        conditions.append(date_filter_conditions)

    # Filter by product_status for statuses that can be filtered in SQL
    # SELLING_DONATION_PHASE and EXPIRED will be filtered in Python
    if product_status:
        if product_status == PRODUCT_STATUS_SELLING:
            conditions.append(Combo.status == COMBO_STATUS_SELLING)
            conditions.append(Combo.is_free == False)
        elif product_status == PRODUCT_STATUS_SELLING_DONATION_PHASE:
            conditions.append(Combo.is_free == True)
        elif product_status == PRODUCT_STATUS_SOLD_DONATION:
            conditions.append(Combo.status == COMBO_STATUS_SOLD)
            conditions.append(Order.status == ORDER_STATUS_PICKED_UP)
            conditions.append(Order.final_price == 0)
        elif product_status == PRODUCT_STATUS_SOLD_PICKED_UP:
            conditions.append(Combo.status == COMBO_STATUS_SOLD)
            conditions.append(Order.status == ORDER_STATUS_PICKED_UP)
            conditions.append(
                or_(
                    Combo.is_free == False,
                    and_(Combo.is_free == True, Order.final_price != 0),
                )
            )
        elif product_status == PRODUCT_STATUS_SOLD_READY_FOR_PICK_UP:
            conditions.append(Combo.status == COMBO_STATUS_SOLD)
            conditions.append(Order.status == ORDER_STATUS_READY_FOR_PICKUP)

    subquery = subquery.where(and_(*conditions)).distinct()

    # Query all combos with all related data needed for DashboardComboData
    order_join = Order.combo_id == Combo.id
    if product_status == PRODUCT_STATUS_EXPIRED:
        order_join = and_(
            Order.combo_id == Combo.id,
            Order.status == ORDER_STATUS_READY_FOR_PICKUP,
        )

    statement = (
        select(
            Combo,
            LockerReservation,
            Order,
            LockerUnit,
            LockerLocation,
            User,
            Shop,
        )
        .outerjoin(LockerReservation, LockerReservation.combo_id == Combo.id)
        .outerjoin(LockerUnit, LockerUnit.id == LockerReservation.locker_unit_id)
        .outerjoin(LockerLocation, LockerLocation.id == LockerUnit.location_id)
        .outerjoin(Order, order_join)
        .outerjoin(User, User.id == Order.user_id)
        .outerjoin(Shop, Shop.id == Combo.shop_id)
        .where(Combo.id.in_(subquery))
        .order_by(desc(Combo.updated_at))
    )

    results = db.exec(statement).all()

    # Extract combos and attach all related data
    # Handle duplicates: one combo may have multiple orders
    combos_data = {}
    for row in results:
        # Extract from Row object: Combo, LockerReservation, Order, LockerUnit, LockerLocation, User, Shop
        combo = row[0] if len(row) > 0 else None
        reservation = row[1] if len(row) > 1 else None
        order = row[2] if len(row) > 2 else None
        locker_unit = row[3] if len(row) > 3 else None
        locker_location = row[4] if len(row) > 4 else None
        user = row[5] if len(row) > 5 else None
        shop = row[6] if len(row) > 6 else None

        if not combo:
            continue

        combo_id = combo.id
        if combo_id not in combos_data:
            # Store all related data for this combo
            combos_data[combo_id] = {
                "combo": combo,
                "reservation": reservation,
                "order": order,
                "locker_unit": locker_unit,
                "locker_location": locker_location,
                "user": user,
                "shop": shop,
            }
        else:
            # Combo already exists, update data if needed
            existing_data = combos_data[combo_id]
            if reservation and not existing_data["reservation"]:
                existing_data["reservation"] = reservation
            if order:
                # Keep order if it's more recent or if no order exists
                if not existing_data["order"]:
                    existing_data["order"] = order
                elif order.created_at > existing_data["order"].created_at:
                    existing_data["order"] = order
            if locker_unit and not existing_data["locker_unit"]:
                existing_data["locker_unit"] = locker_unit
            if locker_location and not existing_data["locker_location"]:
                existing_data["locker_location"] = locker_location
            if user and not existing_data["user"]:
                existing_data["user"] = user
            if shop and not existing_data["shop"]:
                existing_data["shop"] = shop

    return combos_data


def get_reservations_by_combo_ids(
    db: Session, combo_ids: List[str]
) -> Dict[str, LockerReservation]:
    """
    Get reservations by combo IDs, return as dictionary mapping combo_id to reservation.
    Uses batch query for better performance.

    Returns:
        Dictionary mapping combo_id to LockerReservation
    """
    if not combo_ids:
        return {}

    reservations = db.exec(
        select(LockerReservation).where(LockerReservation.combo_id.in_(combo_ids))
    ).all()

    reservations_by_combo_id = {}
    for reservation in reservations:
        if (
            reservation.combo_id
            and reservation.combo_id not in reservations_by_combo_id
        ):
            reservations_by_combo_id[reservation.combo_id] = reservation

    return reservations_by_combo_id


def get_orders_by_combo_ids(
    db: Session, combo_ids: List[str], status: Optional[str] = None
) -> Dict[str, Order]:
    """
    Get orders by combo IDs, return as dictionary mapping combo_id to order.

    Args:
        db: Database session
        combo_ids: List of combo IDs
        status: Optional order status filter

    Returns:
        Dictionary mapping combo_id to Order
    """
    if not combo_ids:
        return {}

    conditions = [Order.combo_id.in_(combo_ids)]
    if status:
        conditions.append(Order.status == status)
    conditions.append(Order.status != ORDER_STATUS_REFUNDED)

    orders = db.exec(select(Order).where(and_(*conditions))).all()

    orders_by_combo_id = {}
    for order in orders:
        if order.combo_id not in orders_by_combo_id:
            orders_by_combo_id[order.combo_id] = order

    return orders_by_combo_id


def get_shops_by_ids(db: Session, shop_ids: List[str]) -> Dict[str, Shop]:
    """
    Get shops by IDs, return as dictionary mapping shop_id to shop.

    Returns:
        Dictionary mapping shop_id to Shop
    """
    if not shop_ids:
        return {}

    shops = db.exec(select(Shop).where(Shop.id.in_(shop_ids))).all()
    return {shop.id: shop for shop in shops}


def filter_combos_by_donation_phase(db: Session, combos: List[Combo]) -> List[Combo]:
    """
    Filter combos that are in SELLING_DONATION_PHASE status.

    This checks if combo is in the donation phase (2/3 of sales duration has passed).
    """
    if not combos:
        return []

    current_time = get_current_time()

    # Batch query all reservations for these combos
    combo_ids = [combo.id for combo in combos]
    reservations_by_combo_id = get_reservations_by_combo_ids(db, combo_ids)

    filtered_combos = []
    for combo in combos:
        reservation = reservations_by_combo_id.get(combo.id)

        if (
            reservation
            and reservation.item_deposited_at
            and reservation.sale_end_time
            and combo.sales_duration
        ):
            duration_seconds = parse_sales_duration_to_seconds(combo.sales_duration)
            two_thirds_duration = duration_seconds * 2 / 3
            donation_start_time = reservation.item_deposited_at + timedelta(
                seconds=two_thirds_duration
            )

            if (
                current_time > donation_start_time
                and current_time < reservation.sale_end_time
            ):
                filtered_combos.append(combo)

    return filtered_combos


def get_combos_by_ids(db, combo_ids: list[str]):
    if not combo_ids:
        return []

    stmt = select(Combo).where(Combo.id.in_(combo_ids))
    return db.exec(stmt).all()


def get_combo_matching_stats_by_date_and_locker(
    db: Session,
    start_date: datetime,
    end_date: datetime,
    locker_unit_ids: List[str],
    include_support_combos: bool = True,
    include_nonsupport_combos: bool = True,
):
    """
    Query orders grouped by date and locker location.
    Returns raw query results (tuples of order_date, location_id, count).
    """
    from sqlmodel import func

    # Build query conditions
    conditions = [
        Order.locker_unit_id.isnot(None),
        Order.locker_unit_id.in_(locker_unit_ids),
        Order.status.in_(REVENUE_COUNTABLE_ORDER_STATUSES),
        Order.status != ORDER_STATUS_REFUNDED,
        func.date(Order.created_at) >= start_date.date(),
        func.date(Order.created_at) <= end_date.date(),
    ]

    # Filter by final_price based on include flags
    price_conditions = []
    if include_support_combos:
        price_conditions.append(Order.final_price == 0)
    if include_nonsupport_combos:
        price_conditions.append(Order.final_price != 0)

    if price_conditions:
        if len(price_conditions) == 1:
            conditions.append(price_conditions[0])
        else:
            # If both are True, use OR to include all orders
            conditions.append(or_(*price_conditions))

    # Query orders grouped by date and locker location
    query = (
        select(
            func.date(Order.created_at).label("order_date"),
            LockerUnit.location_id,
            func.count(Order.id).label("count"),
        )
        .join(LockerUnit, Order.locker_unit_id == LockerUnit.id)
        .where(and_(*conditions))
        .group_by(func.date(Order.created_at), LockerUnit.location_id)
    )

    return db.exec(query).all()
