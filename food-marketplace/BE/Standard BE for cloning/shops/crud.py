from typing import Optional

from sqlalchemy import case
from sqlmodel import Session, col, desc, func, select

from apps.core.constants import (
    COMBO_SALE_HISTORY_STATUSES,
    COMBO_STATUS_EXPIRED,
    COMBO_STATUS_SELLING,
    COMBO_STATUS_SOLD,
)
from apps.core.schemas import DEFAULT_LIMIT, DEFAULT_OFFSET
from apps.lockers.models.location import LockerLocation
from apps.lockers.models.shop_locker_association import ShopLockerAssociation
from apps.products.models import Combo
from apps.shops import schemas
from apps.shops.models.shops import Shop


def get_shop(db: Session, shop_id: str):
    return db.get(Shop, shop_id)


def get_shop_with_users(db: Session, shop_id: str):
    """Get shop with owner and staff relationships loaded"""
    shop = db.get(Shop, shop_id)
    if shop:
        # Trigger relationship loading by accessing them
        _ = shop.owner
        _ = shop.staff_members
    return shop


def get_shop_by_code(db: Session, shop_code: str):
    statement = select(Shop).where(Shop.code == shop_code)
    return db.exec(statement).first()


def update_shop(db: Session, shop: Shop):
    db.add(shop)
    db.commit()
    db.refresh(shop)
    return shop


def get_shops(
    db: Session,
    limit: int = DEFAULT_LIMIT,
    offset: int = DEFAULT_OFFSET,
    name: Optional[str] = None,
):
    # Build query with optional name filter
    query = select(Shop)
    if name:
        query = query.where(col(Shop.name).ilike(f"%{name}%"))

    # Count total shops with filter
    count_query = select(func.count()).select_from(Shop)
    if name:
        count_query = count_query.where(col(Shop.name).ilike(f"%{name}%"))
    total = db.exec(count_query).one()

    # Get paginated shops
    query = query.offset(offset).limit(limit)
    shops = db.exec(query).all()
    return shops, total


def create_shop(db: Session, shop: Shop):
    db.add(shop)
    db.commit()
    db.refresh(shop)
    return shop


def delete_shop(db: Session, shop: Shop):
    shop.is_active = False
    db.add(shop)
    db.commit()


def get_all_active_shops(db: Session):
    """Get all active shops for analytics sync."""
    statement = select(Shop).where(Shop.is_active == True)
    return db.exec(statement).all()

    # """Get all active shops, ordered by name."""
    # statement = select(Shop).where(Shop.is_active == True).order_by(Shop.name)
    # return list(db.exec(statement).all())


def get_shops_by_locker_owner(db: Session, owner_id: str):
    """
    Get shops attached to locker locations owned by a specific user.
    Args:
        db: Database session
        owner_id: ID of the locker owner user
    Returns:
        List of active shops associated with locker locations owned by the user
    """
    stmt = (
        select(Shop)
        .join(ShopLockerAssociation, ShopLockerAssociation.shop_id == Shop.id)
        .join(
            LockerLocation,
            LockerLocation.id == ShopLockerAssociation.locker_location_id,
        )
        .where(LockerLocation.owner_id == owner_id)
        .where(Shop.is_active == True)
        .distinct()
        .order_by(Shop.name)
    )
    return db.exec(stmt).all()


def get_shop_sales_history(db: Session, shop_id: str, filter_date):
    """Get sales history for a shop filtered by date - optimized query without joins"""
    from datetime import datetime

    from sqlmodel import col

    from apps.lockers.models.reservation import LockerReservation
    from apps.lockers.models.unit import LockerUnit
    from apps.orders.models import Order
    from apps.products.models.combos import Combo

    # Add date filter if provided
    if filter_date:
        from datetime import timedelta, timezone

        # Create UTC+9 timezone
        jst = timezone(timedelta(hours=9))

        # Create start/end of day in JST (UTC+9)
        start_of_day_jst = datetime.combine(filter_date, datetime.min.time()).replace(
            tzinfo=jst
        )
        end_of_day_jst = datetime.combine(filter_date, datetime.max.time()).replace(
            tzinfo=jst
        )

        # Convert to UTC for database comparison
        start_of_day_utc = start_of_day_jst.astimezone(timezone.utc).replace(
            tzinfo=None
        )
        end_of_day_utc = end_of_day_jst.astimezone(timezone.utc).replace(tzinfo=None)

        # Filter by item_deposited_at (when product was successfully posted for sale)
        # Join with LockerReservation to filter by posting date
        from sqlalchemy import literal

        sold_statement = (
            select(
                Combo.id.label("id"),
                Combo.name.label("name"),
                Combo.status.label("status"),
                Combo.product_number.label("product_number"),
                Combo.is_free.label("is_free"),
                LockerReservation.created_at.label("posted_at"),
                Order.completed_at.label("sold_at"),
                literal(True).label("is_sold"),
            )
            .join(LockerReservation, LockerReservation.combo_id == Combo.id)
            .join(Order, Order.combo_id == Combo.id)
            .where(Combo.shop_id == shop_id)
            .where(Combo.status == COMBO_STATUS_SOLD)
            .where(Order.completed_at >= start_of_day_utc)
            .where(Order.completed_at <= end_of_day_utc)
        )
        # Case 2: NOT SOLD → filter by LockerReservation.created_at
        not_sold_statement = (
            select(
                Combo.id.label("id"),
                Combo.name.label("name"),
                Combo.status.label("status"),
                Combo.product_number.label("product_number"),
                Combo.is_free.label("is_free"),
                LockerReservation.created_at.label("posted_at"),
                literal(None).label("sold_at"),
                literal(False).label("is_sold"),
            )
            .join(LockerReservation, LockerReservation.combo_id == Combo.id)
            .where(Combo.shop_id == shop_id)
            .where(Combo.status != COMBO_STATUS_SOLD)
            .where(LockerReservation.created_at >= start_of_day_utc)
            .where(LockerReservation.created_at <= end_of_day_utc)
        )

        statement = sold_statement.union_all(not_sold_statement)

        combos = db.exec(statement).all()
        combos = sorted(combos, key=lambda x: x.posted_at or datetime.min, reverse=True)

    else:
        # Get all non-draft combos for the shop without date filter
        statement = (
            select(Combo)
            .where(col(Combo.shop_id) == shop_id)
            .where(col(Combo.status).in_(COMBO_SALE_HISTORY_STATUSES))
            .order_by(desc(Combo.created_at))
        )
        combos = db.exec(statement).all()

    results = []

    for combo in combos:
        # Query reservation and order separately for each combo
        reservation = db.exec(
            select(LockerReservation)
            .where(col(LockerReservation.combo_id) == combo.id)
            .order_by(desc(LockerReservation.created_at))
        ).first()

        locker_unit = None
        if reservation and reservation.locker_unit_id:
            locker_unit = db.get(LockerUnit, reservation.locker_unit_id)

        order = db.exec(select(Order).where(col(Order.combo_id) == combo.id)).first()

        result_data = {
            "sales_end_date": reservation.sale_end_time if reservation else None,
            "status": combo.status,
            "combo_id": combo.id,
            "locker_unit": locker_unit,
            "reservation": reservation,
            "combo_name": combo.name,
            "product_number": combo.product_number,
            "is_free": combo.is_free,
            "order": order,
        }
        results.append(result_data)

    return results


def get_combo_shop(
    db: Session, shop_id: str, is_selling: bool, offset=None, limit=None, user=None
):
    combos_query = db.query(Combo).filter_by(shop_id=shop_id)

    # [SCOPE: FEATURE SOLD_OUT - 20260123] is_selling don't use in current specs.
    # Keep this is_selling params cuz apps already using this param

    # Get total count with same filters
    total = combos_query.count()

    # Order by status priority: SELLING first, then SOLD, then EXPIRED
    status_priority = case(
        (Combo.status == COMBO_STATUS_SELLING, 1),
        (Combo.status == COMBO_STATUS_SOLD, 2),
        (Combo.status == COMBO_STATUS_EXPIRED, 2),
        else_=3,
    )

    time_remaining = func.extract("epoch", Combo.listing_end_date - func.now())
    combos_query = combos_query.order_by(
        status_priority,
        case((Combo.status == COMBO_STATUS_SELLING, time_remaining), else_=None).asc(),
        case(
            (Combo.status != COMBO_STATUS_SELLING, Combo.created_at), else_=None
        ).desc(),
    )

    combos = combos_query.offset(offset).limit(limit).all()

    # Convert to schema and enrich with calculated fields
    from apps.products.utils import (
        populate_combo_pricing_fields,
        populate_combo_timing_fields,
    )

    combo_data = []
    for combo in combos:
        combo_schema = schemas.ShopComboRead.model_validate(combo, from_attributes=True)
        populate_combo_timing_fields(combo_schema, combo)
        populate_combo_pricing_fields(combo_schema, combo, user)
        combo_data.append(combo_schema)

    return combo_data, total


def get_shops_by_location_id(
    db: Session,
    location_id: str,
    limit: int = DEFAULT_LIMIT,
    offset: int = DEFAULT_OFFSET,
):
    """
    Get shops that have sold at least 1 combo at the specified locker location.

    Args:
        db: Database session
        location_id: ID of the locker location
        limit: Number of items per page
        offset: Number of items to skip

    Returns:
        Tuple of (list of Shop objects, total count, set of shop IDs with selling combos)
    """
    from apps.core.utils import get_current_time
    from apps.lockers.models.reservation import LockerReservation
    from apps.lockers.models.unit import LockerUnit

    # Get shop_ids from combos that have been reserved at lockers in this location
    combo_stmt = (
        select(Combo.shop_id)
        .distinct()
        .join(LockerReservation, LockerReservation.combo_id == Combo.id)
        .join(LockerUnit, LockerUnit.id == LockerReservation.locker_unit_id)
        .where(LockerUnit.location_id == location_id)
        .where(Combo.shop_id.isnot(None))
    )
    shop_ids = set(db.exec(combo_stmt).all())

    if not shop_ids:
        return [], 0, set()

    # Get shops by shop_ids
    shop_ids_list = list(shop_ids)
    shop_stmt = (
        select(Shop)
        .where(Shop.id.in_(shop_ids_list))
        .where(Shop.is_active == True)
        .order_by(Shop.name)
    )

    # Get total count
    total_stmt = (
        select(func.count())
        .select_from(Shop)
        .where(Shop.id.in_(shop_ids_list))
        .where(Shop.is_active == True)
    )
    total = db.exec(total_stmt).one()

    # Get paginated shops
    shops = db.exec(shop_stmt.offset(offset).limit(limit)).all()
    paginated_shop_ids = [shop.id for shop in shops]

    # Get count of selling combos per shop at this location
    # Only check for paginated shops to optimize query
    selling_combos_count: dict[str, int] = {}
    if paginated_shop_ids:
        now = get_current_time()
        selling_combo_stmt = (
            select(Combo.shop_id, func.count(Combo.id))
            .join(LockerReservation, LockerReservation.combo_id == Combo.id)
            .join(LockerUnit, LockerUnit.id == LockerReservation.locker_unit_id)
            .where(LockerUnit.location_id == location_id)
            .where(Combo.shop_id.in_(paginated_shop_ids))
            .where(Combo.status == COMBO_STATUS_SELLING)
            .where(Combo.is_draft == False)
            .where(Combo.listing_end_date > now)
            .group_by(Combo.shop_id)
        )
        selling_combos_count = {
            str(shop_id): count
            for shop_id, count in db.exec(selling_combo_stmt).all()
        }

    return list(shops), total, selling_combos_count
