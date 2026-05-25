"""
Order CRUD Operations
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import text
from sqlmodel import Session, desc, select

from .models import Order


def create_order(db: Session, order: Order) -> Order:
    """Create a new order"""
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def get_order_by_id(db: Session, order_id: str) -> Optional[Order]:
    """Get order by ID"""
    return db.get(Order, order_id)


def get_order_by_number(db: Session, order_number: str) -> Optional[Order]:
    """Get order by order number"""
    statement = select(Order).where(Order.order_number == order_number)
    return db.exec(statement).first()


def get_user_orders(
    db: Session,
    user_id: str,
    limit: int = 20,
    offset: int = 0,
    status: Optional[str] = None,
    pickup_start: Optional["datetime"] = None,
    pickup_end: Optional["datetime"] = None,
) -> tuple[List[Order], int]:
    """
    Get orders for a specific user.
    If pickup_start/pickup_end provided, filter by completed_at in JST timezone.
    pickup_start/pickup_end are JST calendar boundaries; completed_at is stored in UTC.
    """
    filters = [Order.user_id == user_id]
    if status:
        filters.append(Order.status == status)

    # If pickup month filter is provided, use JST timezone for completed_at
    if pickup_start is not None and pickup_end is not None:
        completed_at_jst = Order.created_at + text("INTERVAL '9 hours'")
        filters.append(completed_at_jst >= pickup_start)
        filters.append(completed_at_jst < pickup_end)

    base_query = select(Order).where(*filters)

    # Count total
    total = (
        db.exec(base_query).count()
        if hasattr(db, "count")
        else len(db.exec(base_query).all())
    )

    # Get paginated results
    orders = db.exec(
        base_query.order_by(desc(Order.created_at)).offset(offset).limit(limit)
    ).all()

    return list(orders), total


def get_shop_orders(
    db: Session,
    shop_id: str,
    limit: int = 20,
    offset: int = 0,
    status: Optional[str] = None,
) -> tuple[List[Order], int]:
    """Get orders for a specific shop"""
    statement = select(Order).where(Order.shop_id == shop_id)

    if status:
        statement = statement.where(Order.status == status)

    # Get total count
    count_statement = select(Order).where(Order.shop_id == shop_id)
    if status:
        count_statement = count_statement.where(Order.status == status)
    total = len(db.exec(count_statement).all())

    # Get paginated results
    statement = statement.order_by(desc(Order.created_at)).offset(offset).limit(limit)
    orders = db.exec(statement).all()

    return list(orders), total


def update_order(db: Session, order: Order) -> Order:
    """Update an existing order"""
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def _delete_internal_order(db: Session, order: Order):
    db.delete(order)
    db.commit()


def get_order_by_combo(db: Session, combo_id: str) -> Optional[Order]:
    """Get the first order for a specific combo"""
    statement = select(Order).where(Order.combo_id == combo_id)
    return db.exec(statement).first()


def get_pickup_codes_by_locker_units(
    db: Session,
    unit_ids: List[str],
    status: Optional[str] = None,
) -> List[str]:
    """Get pickup codes for orders belonging to the given locker unit IDs.
    Optionally filter by order status."""
    statement = (
        select(Order.pickup_code)
        .where(Order.locker_unit_id.in_(unit_ids))
        .where(Order.pickup_code.is_not(None))
    )
    if status:
        statement = statement.where(Order.status == status)
    return db.exec(statement).all()


def get_orders_by_locker_units_and_date_range(
    db: Session, unit_ids: List[str], start_utc: datetime, end_utc: datetime
) -> List[Order]:
    """Get orders for the given locker unit IDs within a UTC datetime range"""
    return db.exec(
        select(Order).where(
            Order.locker_unit_id.in_(unit_ids),
            Order.created_at >= start_utc,
            Order.created_at <= end_utc,
        )
    ).all()


def get_order_with_related_data(db: Session, order_id: str) -> Optional[dict]:
    """Get order with related shop, combo, and locker data"""
    order = get_order_by_id(db, order_id)
    if not order:
        return None

    result = {"order": order, "shop": None, "combo": None, "locker": None}

    # Get shop data
    if order.shop_id:
        from apps.shops.models.shops import Shop

        shop = db.get(Shop, order.shop_id)
        if shop:
            result["shop"] = {"id": shop.id, "name": shop.name}

    # Get combo data
    if order.combo_id:
        from apps.products.models.combos import Combo

        combo = db.get(Combo, order.combo_id)
        if combo:
            result["combo"] = {
                "id": combo.id,
                "name": combo.name,
                "product_number": combo.product_number,
                "images": combo.images,
            }

    # Get locker data using direct locker_unit_id (more efficient)
    if order.locker_unit_id:
        from apps.lockers.models.unit import LockerUnit

        unit = db.get(LockerUnit, order.locker_unit_id)
        if unit and unit.location:
            result["locker"] = {
                "id": unit.id,
                "name": unit.location.name,
                "unit_number": unit.unit_number,
                "position": unit.location.position,
            }

    return result


def get_latest_free_order(db: Session, user_id: str) -> Optional[Order]:
    """Get the latest order with final_price = 0.0 for a specific user"""
    statement = (
        select(Order)
        .where(Order.user_id == user_id, Order.final_price == 0.0)
        .order_by(desc(Order.created_at))
        .limit(1)
    )
    return db.exec(statement).first()
