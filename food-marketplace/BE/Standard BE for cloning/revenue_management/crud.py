from collections import defaultdict
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import text
from sqlmodel import Session, and_, extract, func, literal, select, union_all

from apps.core.constants import (
    LOCKER_OWNER_REVENUE_PERCENTAGE,
    ORDER_STATUS_PICKED_UP,
    ORDER_STATUS_READY_FOR_PICKUP,
    ORDER_STATUS_REFUNDED,
    REVENUE_COUNTABLE_ORDER_STATUSES,
)
from apps.lockers import ShopLockerAssociation
from apps.lockers.models.location import LockerLocation
from apps.lockers.models.unit import LockerUnit
from apps.orders.models.orders import Order
from apps.shops.models.shops import Shop
from apps.users.models import User


def calculate_revenue_by_month_all_locker_locations(
    db: Session,
    user: User,
    year: str,
    months: List[int],
    all_locker_unit_ids: List[str],
) -> list:

    # convert time utc to get order completed at JST timezone
    completed_at_jst = Order.completed_at + text("INTERVAL '9 hours'")
    base_conditions = [
        func.extract("year", completed_at_jst) == year,
        func.extract("month", completed_at_jst).in_(months),
    ]

    status_filter = [
        Order.status.in_(REVENUE_COUNTABLE_ORDER_STATUSES),
        Order.status != ORDER_STATUS_REFUNDED,
    ]
    # role-based filters
    if user.role in ("admin", "owner_shop"):
        revenue_expr = func.sum(Order.final_price)
    elif user.role == "owner_locker":
        # owner locker own 25% revenue of all orders
        revenue_expr = func.sum(Order.final_price * LOCKER_OWNER_REVENUE_PERCENTAGE)

    base_filter = and_(
        *base_conditions, *status_filter, Order.locker_unit_id.in_(all_locker_unit_ids)
    )

    monthly_stmt = (
        select(
            func.to_char(func.date_trunc("month", completed_at_jst), "MM").label(
                "month"
            ),
            revenue_expr.label("total_final_price"),
        )
        .where(base_filter)
        .group_by(func.date_trunc("month", completed_at_jst))
    )

    total_stmt = select(
        literal("all_months").label("month"),
        revenue_expr.label("total_final_price"),
    ).where(base_filter)

    # Apply locker locations ownership filters
    if user.role == "owner_shop":
        monthly_stmt = monthly_stmt.where(Order.shop_id == user.owned_shop.id)
        total_stmt = total_stmt.where(Order.shop_id == user.owned_shop.id)

    # Execute one time
    stmt = union_all(monthly_stmt, total_stmt).order_by("month")
    results = db.exec(stmt).all()

    return results


def get_accessible_locker_locations_by_role(
    db: Session,
    user: User,
    locker_name: Optional[str] = None,
    location_ids: Optional[List[str]] = None,
    end_date: Optional[datetime] = None,
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
) -> Tuple[List[LockerLocation], List[LockerLocation], int]:

    query = db.query(LockerLocation).filter(LockerLocation.is_active.is_(True))
    if end_date is not None:
        query = query.filter(LockerLocation.created_at < end_date)
    match user.role:
        case "admin":
            pass
        case "owner_locker":
            query = query.filter(LockerLocation.owner_id == user.id)
        case "owner_shop":
            if user.owned_shop:
                query = query.join(ShopLockerAssociation).filter(
                    ShopLockerAssociation.shop_id == user.owned_shop.id
                )
            else:
                return [], [], 0
        case _:
            return [], [], 0

    query = query.order_by(LockerLocation.name.asc())
    if locker_name is not None:
        query = query.filter(LockerLocation.name.ilike(f"%{locker_name}%"))

    all_locations: List[LockerLocation] = query.all()
    total_count = len(all_locations)

    if location_ids:
        all_locations = [loc for loc in all_locations if loc.id in location_ids]
        total_count = len(all_locations)

    paginated_locations = all_locations
    if limit is not None and offset is not None:
        paginated_locations = all_locations[offset : offset + limit]

    return all_locations, paginated_locations, total_count


def get_orders_by_locker_units(
    db: Session,
    locker_unit_ids: List[str],
    user: User,
    year: int,
    months: List[int],
) -> List[Order]:
    """Get orders filtered by locker units, user role, year and months"""

    # convert time utc to get order completed at JST timezone
    completed_at_jst = Order.completed_at + text("INTERVAL '9 hours'")

    # Base query
    statement = select(Order).where(
        and_(
            extract("year", completed_at_jst) == year,
            extract("month", completed_at_jst).in_(months),
            Order.locker_unit_id.in_(locker_unit_ids),
        )
    )

    statement = statement.where(
        Order.status.in_(REVENUE_COUNTABLE_ORDER_STATUSES),
        Order.status != ORDER_STATUS_REFUNDED,
    )

    if user.role == "owner_shop" and getattr(user, "owned_shop", None):
        statement = statement.where(Order.shop_id == user.owned_shop.id)

    orders = db.exec(statement).all()
    return orders


# ===== Shop revenue dashboard helpers =====


def get_shops_with_pagination(
    db: Session,
    shop_ids: Optional[List[str]] = None,
    end_date: Optional[datetime] = None,
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
) -> Tuple[List[Shop], List[Shop], int]:

    query = db.query(Shop).filter(Shop.is_active.is_(True))
    if end_date is not None:
        query = query.filter(Shop.created_at < end_date)
    if shop_ids:
        query = query.filter(Shop.id.in_(shop_ids))

    query = query.order_by(Shop.name.asc())
    all_shops: List[Shop] = query.all()
    total_count = len(all_shops)

    paginated = all_shops
    if limit is not None and offset is not None:
        paginated = all_shops[offset : offset + limit]

    return all_shops, paginated, total_count


def get_orders_by_shops_and_months(
    db: Session,
    shops: List[str],
    year: int,
    months: List[int],
) -> List[Order]:
    # Convert UTC to JST for consistent timezone handling with sales management API
    completed_at_jst = Order.completed_at + text("INTERVAL '9 hours'")

    statement = select(Order).where(
        and_(
            extract("year", completed_at_jst) == year,
            extract("month", completed_at_jst).in_(months),
            Order.shop_id.in_(shops),
            Order.status == ORDER_STATUS_PICKED_UP,
        )
    )
    return db.exec(statement).all()


def get_orders_by_lockers_and_months(
    db: Session,
    lockers: List[str],
    year: int,
    months: List[int],
) -> List[Order]:
    # Convert UTC to JST for consistent timezone handling with sales management API
    completed_at_jst = Order.completed_at + text("INTERVAL '9 hours'")

    statement = (
        select(Order, LockerUnit.location_id)
        .join(
            LockerUnit,
            LockerUnit.id == Order.locker_unit_id,
        )
        .where(
            and_(
                extract("year", completed_at_jst) == year,
                extract("month", completed_at_jst).in_(months),
                LockerUnit.location_id.in_(lockers),
                Order.status == ORDER_STATUS_PICKED_UP,
            )
        )
    )

    return db.exec(statement).all()


def get_shops(
    db: Session,
    shop_ids: Optional[List[str]] = None,
    end_date: Optional[datetime] = None,
) -> Tuple[List[Shop], int]:

    query = db.query(Shop).filter(Shop.is_active.is_(True))
    # if end_date is not None:
    #     query = query.filter(Shop.created_at < end_date)
    if shop_ids:
        query = query.filter(Shop.id.in_(shop_ids))

    query = query.order_by(Shop.name.asc())
    shops: List[Shop] = query.all()

    return shops


def get_lockers(
    db: Session,
    locker_ids: Optional[List[str]] = None,
    end_date: Optional[datetime] = None,
) -> Tuple[List[Shop], int]:

    query = db.query(LockerLocation).filter(LockerLocation.is_active.is_(True))
    # if end_date is not None:
    #     query = query.filter(LockerLocation.created_at < end_date)
    if locker_ids:
        query = query.filter(LockerLocation.id.in_(locker_ids))

    query = query.order_by(LockerLocation.name.asc())
    lockers: List[LockerLocation] = query.all()

    return lockers


def get_locker_shop_structure(db: Session) -> dict:
    """
    Get locker-shop structure from shop_locker_associations table.

    Returns a dict mapping locker_location_id to list of shop_ids.

    Args:
        db: Database session

    Returns:
        Dict mapping locker_location_id to list of shop_ids
    """
    statement = select(ShopLockerAssociation)
    associations = db.exec(statement).all()

    locker_shop_map = defaultdict(list)
    for assoc in associations:
        locker_shop_map[assoc.locker_location_id].append(assoc.shop_id)

    return dict(locker_shop_map)


def get_accessible_locker_ids(
    db: Session, user: User, locker_location_ids: Optional[List[str]] = None
) -> tuple:
    """
    Get accessible locker location IDs based on user role.

    Args:
        db: Database session
        user: User object with role and id
        locker_location_ids: Optional list of locker location IDs to filter

    Returns:
        Tuple of (filtered_locker_ids, invalid_ids)
    """
    # Get accessible locker IDs based on user role
    if user.role == "owner_locker":
        # Owner locker can only access their own lockers from shop_locker_associations
        statement = (
            select(ShopLockerAssociation.locker_location_id)
            .distinct()
            .outerjoin(
                LockerLocation,
                ShopLockerAssociation.locker_location_id == LockerLocation.id,
            )
            .where(LockerLocation.owner_id == user.id)
        )
        accessible_locker_ids_list = db.exec(statement).all()
    else:
        # Admin can access all lockers from shop_locker_associations
        statement = select(ShopLockerAssociation.locker_location_id).distinct()
        accessible_locker_ids_list = db.exec(statement).all()

    accessible_locker_ids = set(accessible_locker_ids_list)

    if locker_location_ids:
        filtered_locker_ids = [
            lid for lid in locker_location_ids if lid in accessible_locker_ids
        ]
        invalid = set(locker_location_ids) - accessible_locker_ids
        return filtered_locker_ids, invalid

    return list(accessible_locker_ids), set()


def get_shop_ids_by_order_locations(db: Session, location_ids: List[str]) -> List[str]:
    """
    Get distinct shop IDs combined from:
    1. Historical orders placed at specific locker locations.
    2. Current associations in ShopLockerAssociation.

    Args:
        db: Database session
        location_ids: List of locker location IDs

    Returns:
        List of distinct shop IDs
    """
    # 1. Shop IDs from historical orders
    order_stmt = (
        select(Order.shop_id)
        .distinct()
        .join(LockerUnit, LockerUnit.id == Order.locker_unit_id)
        .where(LockerUnit.location_id.in_(location_ids))
    )
    shop_ids_1 = set(db.exec(order_stmt).all())

    # 2. Shop IDs from current associations
    assoc_stmt = (
        select(ShopLockerAssociation.shop_id)
        .distinct()
        .where(ShopLockerAssociation.locker_location_id.in_(location_ids))
    )
    shop_ids_2 = set(db.exec(assoc_stmt).all())

    # Return union of both sets
    return list(shop_ids_1 | shop_ids_2)


def get_locker_and_shop_names(
    db: Session, locker_ids: List[str], shop_ids: List[str]
) -> tuple:
    """
    Fetch locker and shop names from database.

    Args:
        db: Database session
        locker_ids: List of locker location IDs
        shop_ids: List of shop IDs

    Returns:
        Tuple of (locker_name_map, shop_name_map)
    """
    # Fetch locker names
    locker_stmt = select(LockerLocation).where(LockerLocation.id.in_(locker_ids))
    lockers = db.exec(locker_stmt).all()
    locker_name_map = {loc.id: loc.name for loc in lockers}

    # Fetch shop names
    shop_stmt = select(Shop).where(Shop.id.in_(shop_ids))
    shops = db.exec(shop_stmt).all()
    shop_name_map = {shop.id: shop.name for shop in shops}

    return locker_name_map, shop_name_map


def get_orders_with_users_by_lockers(
    db: Session, locker_ids: List[str], start_date: datetime, end_date: datetime
):
    """
    Get orders with user information for specified lockers within date range.
    start_date/end_date are JST calendar boundaries; completed_at is stored in UTC.
    Filter by JST for consistency with sales/revenue APIs.
    """
    from apps.lockers.models.unit import LockerUnit
    from apps.users.models import User

    completed_at_jst = Order.completed_at + text("INTERVAL '9 hours'")
    statement = (
        select(Order, User, LockerUnit.location_id)
        .outerjoin(User, Order.user_id == User.id)
        .join(LockerUnit, Order.locker_unit_id == LockerUnit.id)
        .where(
            and_(
                LockerUnit.location_id.in_(locker_ids),
                completed_at_jst >= start_date,
                completed_at_jst <= end_date,
                Order.status == ORDER_STATUS_PICKED_UP,
            )
        )
    )

    results = db.exec(statement).all()
    return results


def get_orders_with_users_by_shops(
    db: Session, shop_ids: List[str], start_date: datetime, end_date: datetime
):
    """
    Get orders with user information for specified shops within date range.
    start_date/end_date are JST calendar boundaries; completed_at is stored in UTC.
    Filter by JST for consistency with sales/revenue APIs.
    """
    from apps.users.models import User

    completed_at_jst = Order.completed_at + text("INTERVAL '9 hours'")
    statement = (
        select(Order, User, Order.shop_id)
        .outerjoin(User, Order.user_id == User.id)
        .where(
            and_(
                Order.shop_id.in_(shop_ids),
                completed_at_jst >= start_date,
                completed_at_jst <= end_date,
                Order.status == ORDER_STATUS_PICKED_UP,
            )
        )
    )

    results = db.exec(statement).all()
    return results


def get_orders_by_shops_with_date_range(
    db: Session, shop_ids: List[str], start_date: datetime, end_date: datetime
):
    """
    Get completed orders for specified shops within date range.
    start_date/end_date are JST calendar boundaries; completed_at is stored in UTC.
    Filter by JST for consistency with sales/revenue APIs.
    """
    completed_at_jst = Order.completed_at + text("INTERVAL '9 hours'")
    statement = select(Order).where(
        and_(
            Order.shop_id.in_(shop_ids),
            completed_at_jst >= start_date,
            completed_at_jst <= end_date,
            Order.status.in_(REVENUE_COUNTABLE_ORDER_STATUSES),
            Order.status != ORDER_STATUS_REFUNDED,
        )
    )

    results = db.exec(statement).all()
    return results
