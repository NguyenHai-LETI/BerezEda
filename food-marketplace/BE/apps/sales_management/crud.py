"""
Sales Management CRUD Operations

Database operations for sales management functionality.
Provides abstraction layer for complex queries needed for sales analytics,
dashboard data, and item filtering operations.
"""

from datetime import date, datetime, time, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import text
from sqlmodel import Session, and_, col, desc, select

from apps.core.constants import (
    COMBO_STATUS_DELETED,
    COMBO_STATUS_EXPIRED,
    COMBO_STATUS_EXPIRED_PUT_IN_LOCKER,
    COMBO_STATUS_SOLD,
    ORDER_STATUS_PICKED_UP,
    RESERVATION_STATUS_CANCELLED,
    RESERVATION_STATUS_COMPLETED,
)
from apps.core.utils import get_current_time
from apps.lockers.models.location import LockerLocation
from apps.lockers.models.reservation import LockerReservation
from apps.lockers.models.unit import LockerUnit
from apps.orders.models.orders import Order
from apps.products.models.combos import Combo


def get_shop_combos_by_date_range(
    db: Session,
    shop_id: str,
    start_date: datetime,
    end_date: datetime,
    product_number: Optional[str] = None,
    name: Optional[str] = None,
    locker_name: Optional[str] = None,
    search: Optional[str] = None,
) -> List[Combo]:
    """Get all combos for a shop within a date range with orders efficiently loaded.

    Note: start_date and end_date should already be converted from JST to UTC
    by the caller if needed.
    """
    # Normalize start_date -> 00:00:00
    start_date = datetime.combine(start_date.date(), time.min)

    # Normalize end_date -> 23:59:59
    end_date = datetime.combine(end_date.date(), time(23, 59, 59))

    # Build base conditions
    conditions = [
        Combo.shop_id == shop_id,
        (Order.completed_at + text("INTERVAL '9 hours'")) >= start_date,
        (Order.completed_at + text("INTERVAL '9 hours'")) <= end_date,
        Combo.status == COMBO_STATUS_SOLD,
    ]

    # Add filter conditions
    if product_number is not None:
        conditions.append(Combo.product_number == product_number)

    if name is not None and search is None:
        # Specific name search (only if no general search)
        conditions.append(Combo.name.contains(name))

    # Build query with base joins
    query = select(Combo).join(Order, Order.combo_id == Combo.id, isouter=True)

    # Add locker joins and conditions if locker_name filter is needed
    locker_conditions = []
    if locker_name is not None:
        locker_conditions.append(LockerLocation.name.contains(locker_name))
        query = (
            query.join(LockerReservation, Combo.id == LockerReservation.combo_id)
            .join(LockerUnit, LockerReservation.locker_unit_id == LockerUnit.id)
            .join(LockerLocation, LockerUnit.location_id == LockerLocation.id)
        )

    # Apply all conditions
    if locker_conditions:
        conditions.extend(locker_conditions)

    query = query.where(and_(*conditions))

    combos = db.exec(query).all()

    return list(combos)


def get_shop_combos(
    db: Session,
    shop_id: str,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    search: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    product_number: Optional[str] = None,
    name: Optional[str] = None,
    locker_name: Optional[str] = None,
    status: Optional[str] = None,
) -> Tuple[List[Combo], int]:
    """
    Unified function to get shop combos with optional search functionality.

    Args:
        db: Database session
        shop_id: Shop ID to filter by
        limit: Maximum number of results to return
        offset: Number of results to skip
        search: Optional search term to filter by name or product number (legacy)
        start_date: Filter by combo created_at >= start_date
        end_date: Filter by combo created_at <= end_date
        product_number: Filter by exact product_number match
        name: Filter by combo name (partial match)
        statuses: List of statuses to filter by (defaults to unsold statuses)

    Returns:
        Tuple of (combos_list, total_count)
    """
    # Default to unsold statuses if not specified
    conditions = [Combo.shop_id == shop_id, Combo.is_draft == False]

    # display combos with status DELETED when not specify combo status (in unsold screen in app)
    if status is not None:
        conditions.append(Combo.status == status)
        conditions.append(Combo.status != COMBO_STATUS_DELETED)

    # Add specific field filters
    if product_number is not None:
        conditions.append(Combo.product_number == product_number)

    if name is not None and search is None:
        # Specific name search (only if no general search)
        conditions.append(Combo.name.contains(name))

    elif search is not None:
        # General search across name and product_number (takes precedence)
        search_condition = Combo.name.contains(search) | Combo.product_number.contains(
            search
        )
        conditions.append(search_condition)

    # --- Date range filters based on item_deposited_at (when product was posted for sale) ---
    date_filter_needed = start_date is not None or end_date is not None

    # --- Locker filters ---
    locker_conditions = []
    if locker_name is not None:
        locker_conditions.append(LockerLocation.name.contains(locker_name))

    # Build query with all conditions
    # Only join with Order and filter by picked_up status when status is not None
    if status is not None:
        # Join with Order to filter by picked_up status
        # Also join with LockerReservation if date filter is needed
        if date_filter_needed:
            query = (
                select(Combo)
                .join(Order)
                .join(LockerReservation, Combo.id == LockerReservation.combo_id)
                .where(and_(*conditions, Order.status == ORDER_STATUS_PICKED_UP))
            )

            # Add date filters based on item_deposited_at
            if start_date is not None:
                query = query.where(col(Order.completed_at) >= start_date)
            if end_date is not None:
                query = query.where(col(Order.completed_at) <= end_date)

            query = query.order_by(desc(Order.completed_at))

            # Count total with same conditions
            count_query = (
                select(Combo)
                .join(Order)
                .join(LockerReservation, Combo.id == LockerReservation.combo_id)
                .where(and_(*conditions, Order.status == ORDER_STATUS_PICKED_UP))
            )
            if start_date is not None:
                count_query = count_query.where(col(Order.completed_at) >= start_date)
            if end_date is not None:
                count_query = count_query.where(col(Order.completed_at) <= end_date)
        else:
            query = (
                select(Combo)
                .join(Order)
                .where(and_(*conditions, Order.status == ORDER_STATUS_PICKED_UP))
                .order_by(desc(Combo.created_at))
            )

            # Count total with same conditions
            count_query = (
                select(Combo)
                .join(Order)
                .where(and_(*conditions, Order.status == ORDER_STATUS_PICKED_UP))
            )
    else:
        # Get all Combos, including those without Orders, but exclude Combos with picked up Orders
        if date_filter_needed:
            query = (
                select(Combo)
                .outerjoin(Order)  # LEFT JOIN to include Combos without Orders
                .join(LockerReservation, Combo.id == LockerReservation.combo_id)
                .where(
                    and_(
                        *conditions,
                        # Include Combos with no Orders OR Orders that are not picked up
                        (Order.status == None)
                        | (Order.status != ORDER_STATUS_PICKED_UP)
                    )
                )
            )

            # Add date filters based on item_deposited_at
            if start_date is not None:
                query = query.where(col(LockerReservation.created_at) >= start_date)
            if end_date is not None:
                query = query.where(col(LockerReservation.created_at) <= end_date)

            query = query.order_by(desc(LockerReservation.created_at))
            # Count total with same conditions
            count_query = (
                select(Combo)
                .outerjoin(Order)
                .join(LockerReservation, Combo.id == LockerReservation.combo_id)
                .where(
                    and_(
                        *conditions,
                        (Order.status == None)
                        | (Order.status != ORDER_STATUS_PICKED_UP)
                    )
                )
            )
            if start_date is not None:
                count_query = count_query.where(
                    col(LockerReservation.created_at) >= start_date
                )
            if end_date is not None:
                count_query = count_query.where(
                    col(LockerReservation.created_at) <= end_date
                )
        else:
            query = (
                select(Combo)
                .outerjoin(Order)  # LEFT JOIN to include Combos without Orders
                .where(
                    and_(
                        *conditions,
                        # Include Combos with no Orders OR Orders that are not picked up
                        (Order.status == None)
                        | (Order.status != ORDER_STATUS_PICKED_UP)
                    )
                )
                .order_by(desc(Combo.created_at))
            )

            # Count total with same conditions
            count_query = (
                select(Combo)
                .outerjoin(Order)
                .where(
                    and_(
                        *conditions,
                        (Order.status == None)
                        | (Order.status != ORDER_STATUS_PICKED_UP)
                    )
                )
            )

    if locker_conditions:
        query = (
            query.join(LockerUnit, Order.locker_unit_id == LockerUnit.id)
            .join(LockerLocation, LockerUnit.location_id == LockerLocation.id)
            .where(and_(*locker_conditions))
        )
        count_query = (
            count_query.join(LockerUnit, Order.locker_unit_id == LockerUnit.id)
            .join(LockerLocation, LockerUnit.location_id == LockerLocation.id)
            .where(and_(*locker_conditions))
        )

    total = len(db.exec(count_query).all())

    # Apply pagination if provided
    if offset is not None:
        query = query.offset(offset)
    if limit is not None:
        query = query.limit(limit)

    combos = db.exec(query).all()
    return list(combos), total


def get_combo_with_locker_info(
    db: Session, combo_id: str
) -> Optional[Tuple[Combo, Optional[LockerUnit], Optional[LockerLocation]]]:
    """Get combo with associated locker unit and location information."""
    combo = db.get(Combo, combo_id)
    if not combo:
        return None

    # Get locker reservation
    reservation = db.exec(
        select(LockerReservation).where(LockerReservation.combo_id == combo_id)
    ).first()

    if not reservation:
        return combo, None, None

    # Get locker unit
    unit = db.get(LockerUnit, reservation.locker_unit_id)
    if not unit:
        return combo, None, None

    # Get location
    location = db.get(LockerLocation, unit.location_id)

    return combo, unit, location


def get_recent_sales(db: Session, shop_id: str, hours: int = 24) -> List[Combo]:
    """Get recent sales within specified hours."""
    cutoff = get_current_time() - timedelta(hours=hours)
    combos = db.exec(
        select(Combo).where(
            and_(
                Combo.shop_id == shop_id,
                Combo.status == COMBO_STATUS_SOLD,
                Combo.updated_at >= cutoff,
            )
        )
    ).all()
    return list(combos)


def get_expiring_combos(db: Session, shop_id: str, hours: int = 2) -> List[Combo]:
    """Get combos expiring within specified hours."""
    cutoff = get_current_time() + timedelta(hours=hours)
    # Get all combos and filter in Python to avoid SQLModel issues
    all_combos = db.exec(
        select(Combo).where(
            and_(
                Combo.shop_id == shop_id,
                Combo.status == COMBO_STATUS_EXPIRED,
            )
        )
    ).all()

    return all_combos


def get_combo_by_id_and_shop(
    db: Session, combo_id: str, shop_id: str
) -> Optional[Combo]:
    """Get combo by ID ensuring it belongs to the specified shop."""
    return db.exec(
        select(Combo).where(and_(Combo.id == combo_id, Combo.shop_id == shop_id))
    ).first()


def cleanup_old_reservations(
    db: Session, cutoff_date: datetime, batch_size: int = 500
) -> int:
    """
    Clean up old locker reservations that are no longer needed.
    Returns the number of deleted reservations.
    """
    stmt = (
        select(LockerReservation)
        .where(
            col(LockerReservation.created_at) < cutoff_date,
            col(LockerReservation.status).in_(
                [RESERVATION_STATUS_COMPLETED, RESERVATION_STATUS_CANCELLED]
            ),
        )
        .limit(batch_size)
    )

    old_reservations = list(db.exec(stmt))
    deleted_count = 0

    for reservation in old_reservations:
        db.delete(reservation)
        deleted_count += 1

    return deleted_count


def generate_sales_report_data(db: Session, report_date: date) -> dict:
    """
    Generate sales report data for a specific date.
    Returns summary statistics for the day.
    """
    from apps.products.models import Combo

    # Define date range for the report
    start_date = datetime.combine(report_date, datetime.min.time())
    end_date = start_date + timedelta(days=1)

    # Get sold combos for the date
    sold_combos_stmt = select(Combo).where(
        col(Combo.status) == COMBO_STATUS_SOLD,
        col(Combo.updated_at) >= start_date,
        col(Combo.updated_at) < end_date,
    )

    sold_combos = list(db.exec(sold_combos_stmt))

    # Calculate statistics
    total_sales = len(sold_combos)
    total_revenue = sum(
        combo.original_price or 0 for combo in sold_combos if not combo.is_free
    )
    total_donations = len([combo for combo in sold_combos if combo.is_free])

    return {
        "total_sales": total_sales,
        "total_revenue": float(total_revenue),
        "total_donations": total_donations,
        "average_price": float(total_revenue / total_sales) if total_sales > 0 else 0,
    }


def get_recent_sales_count(db: Session, shop_id: str, hours: int = 24) -> int:
    """Get count of sales in the last N hours."""
    cutoff_time = get_current_time() - timedelta(hours=hours)

    stmt = select(Combo).where(
        Combo.shop_id == shop_id,
        Combo.updated_at >= cutoff_time,
    )

    recent_sales = list(db.exec(stmt))
    return len(recent_sales)


def get_pending_placement_count(db: Session, shop_id: str) -> int:
    """Get count of items pending locker placement."""
    stmt = select(Combo).where(
        Combo.shop_id == shop_id, Combo.status == COMBO_STATUS_EXPIRED_PUT_IN_LOCKER
    )

    pending_combos = list(db.exec(stmt))
    return len(pending_combos)


def get_expiring_soon_count(db: Session, shop_id: str, hours: int = 2) -> int:
    """Get count of items expiring within N hours."""
    cutoff_time = get_current_time() + timedelta(hours=hours)

    stmt = select(Combo).where(
        Combo.shop_id == shop_id,
        col(Combo.status).in_(["active", "selling"]),
        col(Combo.listing_end_date).is_not(None),
        col(Combo.listing_end_date) <= cutoff_time,
    )

    expiring_combos = list(db.exec(stmt))
    return len(expiring_combos)
