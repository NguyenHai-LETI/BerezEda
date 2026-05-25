from typing import Optional

from sqlalchemy import and_, case, func, or_
from sqlmodel import Session, col, desc, select

from apps.core.constants import (
    COMBO_NOT_IN_LOCKER_LOCATION_STATUSES,
    COMBO_PURCHASABLE_STATUSES,
    COMBO_STATUS_EXPIRED,
    COMBO_STATUS_SELLING,
    COMBO_STATUS_SOLD,
)
from apps.core.utils import get_current_time
from apps.lockers.models.reservation import LockerReservation
from apps.orders.models import Order
from apps.products.models import Combo, ComboProduct, ProductMaster
from apps.shops.models.shops import Shop


def get_combo_by_id(db: Session, combo_id: str):
    return db.get(Combo, combo_id)


def get_combo_with_products(db: Session, combo_id: str):
    """Get combo with loaded product relationships for response serialization"""
    combo = db.get(Combo, combo_id)
    if combo:
        combo_products = db.exec(
            select(ComboProduct).where(ComboProduct.combo_id == combo_id)
        ).all()

        combo.combo_products = list(combo_products)

    return combo


def get_combo_with_product_masters(db: Session, combo_id: str):
    """Get combo with loaded product relationships including product master details and shop"""
    combo = db.get(Combo, combo_id)
    if combo:
        # Load shop relationship
        combo.shop = db.get(Shop, combo.shop_id)

        combo_products = db.exec(
            select(ComboProduct).where(ComboProduct.combo_id == combo_id)
        ).all()

        # Load product masters for each combo product
        for combo_product in combo_products:
            combo_product.product_master = db.get(
                ProductMaster, combo_product.product_master_id
            )

        combo.combo_products = list(combo_products)

        # DEBUG: Print loaded combo_products for this combo
        print(
            f"[DEBUG] Combo {combo_id} loaded {len(combo_products)} combo_products: {[cp.id for cp in combo_products]}"
        )

    return combo


def get_combos(
    db: Session,
    user=None,
    limit: int = 20,
    offset: int = 0,
    is_draft: Optional[bool] = None,
):
    statement = select(Combo).where(Combo.is_available == True)

    # Filter by draft status if specified
    if is_draft is not None:
        statement = statement.where(Combo.is_draft == is_draft)

    # Filter by user's shops for shop owners and staff
    user_shop = user.get_associated_shop() if user else None
    if user and user.role != "admin" and user_shop:
        statement = statement.where(Combo.shop_id == user_shop.id)

    # Get total count
    count_statement = select(Combo).where(Combo.is_available == True)
    if is_draft is not None:
        count_statement = count_statement.where(Combo.is_draft == is_draft)
    if user and user.role != "admin" and user_shop:
        count_statement = count_statement.where(Combo.shop_id == user_shop.id)

    total = len(db.exec(count_statement).all())

    # Get paginated results ordered by newest first
    statement = statement.order_by(desc(Combo.created_at)).offset(offset).limit(limit)
    combos = db.exec(statement).all()

    return combos, total


def get_public_combos(
    db: Session,
    limit: int = 20,
    offset: int = 0,
    shop_id: Optional[str] = None,
    category: Optional[str] = None,
    include_sold_out: Optional[bool] = None,
):
    """Get publicly available combos for customers to purchase"""

    filtered_combo = COMBO_PURCHASABLE_STATUSES.copy()

    # [SOLDOUT FEATURE] For case display and selling combos and sold-out combo in home screen
    if include_sold_out and include_sold_out == True:
        filtered_combo.append(COMBO_STATUS_SOLD)

    # Always include EXPIRED status combos
    filtered_combo.append(COMBO_STATUS_EXPIRED)

    statement = select(Combo)

    # Only show non-draft combos that are available for purchase
    statement = statement.where(
        Combo.is_draft == False,
        # Combo.is_available == True,
        col(Combo.status).in_(filtered_combo),
    )

    now = get_current_time()

    # Only show combos that are still within sales time (before listing_end_date) for selling combos
    # EXPIRED combos are always shown regardless of listing_end_date
    statement = statement.where(
        or_(
            and_(Combo.status == COMBO_STATUS_SOLD),
            and_(Combo.status == COMBO_STATUS_EXPIRED),
            and_(
                Combo.status == COMBO_STATUS_SELLING,
                col(Combo.listing_end_date) > now,
            ),
        )
    )

    # Filter by shop if specified
    if shop_id:
        statement = statement.where(col(Combo.shop_id) == shop_id)

    # Filter by category if specified
    if category:
        statement = statement.where(col(Combo.category) == category)

    # For now, skip location filtering to avoid complex joins
    # You can implement this later if needed

    # Get total count with same filters
    count_statement = select(Combo).where(
        Combo.is_draft == False,
        # Combo.is_available == True,
        col(Combo.status).in_(filtered_combo),
    )

    # Apply same time filter to count (only for SELLING status)
    # EXPIRED combos are always included in count
    count_statement = count_statement.where(
        or_(
            Combo.status == COMBO_STATUS_EXPIRED,
            Combo.status != COMBO_STATUS_SELLING,
            and_(
                Combo.status == COMBO_STATUS_SELLING,
                col(Combo.listing_end_date) > get_current_time(),
            ),
        )
    )

    if shop_id:
        count_statement = count_statement.where(col(Combo.shop_id) == shop_id)
    if category:
        count_statement = count_statement.where(col(Combo.category) == category)

    total = len(db.exec(count_statement).all())

    # Get paginated results ordered by status priority (SOLD at the end) then by date
    # Priority: 0 = non-SOLD (SELLING, etc), 1 = SOLD, EXPIRED
    status_priority = case(
        (Combo.status == COMBO_STATUS_SOLD, 1),
        else_=0,
    )

    order_time = case(
        (Combo.status == COMBO_STATUS_SOLD, Combo.updated_at),
        else_=Combo.listing_end_date,
    )

    statement = (
        statement.order_by(
            status_priority.asc(),
            order_time.desc(),
        )
        .offset(offset)
        .limit(limit)
    )
    combos = db.exec(statement).all()
    return combos, total


def get_combos_by_locker_location(
    db: Session,
    location_id: str,
    limit: int = 20,
    offset: int = 0,
    category: Optional[str] = None,
    is_selling: Optional[bool] = None,
):
    """Get all combos assigned to lockers in a specific location"""
    from apps.lockers.models.reservation import LockerReservation
    from apps.lockers.models.unit import LockerUnit

    # Build query with joins to get combos through locker reservations
    # Include EXPIRED status combos (remove EXPIRED from exclusion list)
    excluded_statuses = [
        status
        for status in COMBO_NOT_IN_LOCKER_LOCATION_STATUSES
        if status != COMBO_STATUS_EXPIRED
    ]

    statement = (
        select(Combo)
        .join(LockerReservation)
        .join(LockerUnit)
        .where(
            LockerUnit.location_id == location_id,
            LockerReservation.combo_id == Combo.id,
            LockerReservation.locker_unit_id == LockerUnit.id,
            Combo.is_draft == False,
            col(Combo.status).notin_(excluded_statuses),
        )
    )

    # one_day_ago = datetime.utcnow() - timedelta(hours=HIDE_SOLD_OUT_COMBO_TIME)

    # Subquery: get combo SOLD has completed more than 1 day (not use in current spec)
    sold_old_combos_subquery = (
        select(Combo.id)
        .join(LockerReservation, LockerReservation.combo_id == Combo.id)
        .join(LockerUnit, LockerUnit.id == LockerReservation.locker_unit_id)
        .join(Order, Order.combo_id == Combo.id)
        .where(
            LockerUnit.location_id == location_id,
            Combo.status == COMBO_STATUS_SOLD,
            Order.completed_at.isnot(None),
            # Order.completed_at < one_day_ago,
        )
    )

    # [SCOPE: FEATURE SOLD_OUT - 20260123] is_selling don't use in current specs.
    # Keep this params cuz apps already using this param

    # Optional selling filter
    # if is_selling:
    #     statement = statement.where(Combo.status == COMBO_STATUS_SELLING).order_by(
    #         Combo.listing_end_date.asc()
    #     )
    # Exclude SOLD combos older than 1 day
    # statement = statement.where(~Combo.id.in_(sold_old_combos_subquery))

    # Filter by category if specified
    if category:
        statement = statement.where(Combo.category == category)

    # Get total count with same filters
    count_statement = select(func.count()).select_from(statement.subquery())
    total = db.exec(count_statement).first()

    # Order by status priority: SELLING first, then SOLD and EXPIRED (same priority)
    status_priority = case(
        (Combo.status == COMBO_STATUS_SELLING, 1),
        (Combo.status == COMBO_STATUS_SOLD, 2),
        (Combo.status == COMBO_STATUS_EXPIRED, 2),
        else_=3,
    )

    time_remaining = func.extract("epoch", Combo.listing_end_date - func.now())
    statement = (
        statement.order_by(
            status_priority,
            case(
                (Combo.status == COMBO_STATUS_SELLING, time_remaining), else_=None
            ).asc(),
            case(
                (Combo.status != COMBO_STATUS_SELLING, Combo.created_at), else_=None
            ).desc(),
        )
        .offset(offset)
        .limit(limit)
    )
    combos = db.exec(statement).all()

    return combos, total


def get_combos_for_management(db: Session, user, limit: int = 20, offset: int = 0):
    """Get combos for shop management - only shop owner's combos"""
    query = db.query(Combo).filter(Combo.is_available.is_(True))

    # Filter by user's shops for management operations
    user_shop = user.get_associated_shop() if user else None
    if user and user.role != "admin" and user_shop:
        query = query.filter(Combo.shop_id == user_shop.id)

    total = query.count()
    combos = query.offset(offset).limit(limit).all()
    return combos, total


def create_combo(db: Session, combo: Combo):
    db.add(combo)
    db.commit()
    db.refresh(combo)
    return combo


def create_combo_product(db: Session, combo_product: ComboProduct):
    db.add(combo_product)
    db.commit()
    db.refresh(combo_product)
    return combo_product


def delete_combo_products(db: Session, combo_id: str):
    """Delete all products for a combo"""
    statement = select(ComboProduct).where(ComboProduct.combo_id == combo_id)
    combo_products = db.exec(statement).all()
    for cp in combo_products:
        db.delete(cp)
    db.commit()


def update_combo(db: Session, combo: Combo):
    db.add(combo)
    db.commit()
    db.refresh(combo)
    return combo


def delete_combo(db: Session, combo: Combo):
    if combo.is_draft:
        # Hard delete for draft combos - also delete associated combo products
        from apps.products.models.combo_products import ComboProduct

        # Delete all combo products first
        combo_products_stmt = select(ComboProduct).where(
            ComboProduct.combo_id == combo.id
        )
        combo_products = db.exec(combo_products_stmt).all()
        for combo_product in combo_products:
            db.delete(combo_product)

        # Then delete the combo
        db.delete(combo)
    else:
        # Per spec: Set status to DELETED for non-draft combos
        from apps.core.constants import COMBO_STATUS_DELETED

        combo.status = COMBO_STATUS_DELETED
        combo.is_available = False
        combo.updated_at = get_current_time()
        db.add(combo)
    db.commit()


def get_product_master(db: Session, product_master_id: str):
    return db.get(ProductMaster, product_master_id)


def get_product_master_by_name_and_shop(
    db: Session, name: str, shop_id: str, exclude_id: Optional[str] = None
):
    """Check if product master with given name already exists for the shop"""
    query = select(ProductMaster).where(
        ProductMaster.name == name, ProductMaster.shop_id == shop_id
    )

    # Exclude current product when updating
    if exclude_id:
        query = query.where(ProductMaster.id != exclude_id)

    return db.exec(query).first()


def get_combo_products_by_product_master(db: Session, product_master_id: str):
    """Get combo products that reference this product master"""
    return db.exec(
        select(ComboProduct).where(ComboProduct.product_master_id == product_master_id)
    ).all()


def get_product_masters(
    db: Session, user=None, name: str | None = None, limit: int = 20, offset: int = 0
):
    statement = select(ProductMaster).where(ProductMaster.is_active == True)

    if user and user.role != "admin":
        # Filter by shop for both staff and owner users using get_associated_shop method
        user_shop = user.get_associated_shop() if user else None
        if user_shop:
            statement = statement.where(ProductMaster.shop_id == user_shop.id)

    if name and name.strip():
        search_term = f"%{name.strip()}%"
        statement = statement.where(col(ProductMaster.name).ilike(search_term))

    # Get total count with same filters
    count_statement = select(ProductMaster).where(ProductMaster.is_active == True)
    if user and user.role != "admin":
        user_shop = user.get_associated_shop() if user else None
        if user_shop:
            count_statement = count_statement.where(
                ProductMaster.shop_id == user_shop.id
            )
    if name and name.strip():
        search_term = f"%{name.strip()}%"
        count_statement = count_statement.where(
            col(ProductMaster.name).ilike(search_term)
        )

    total = len(db.exec(count_statement).all())

    # Get paginated results ordered by newest first
    statement = (
        statement.order_by(desc(ProductMaster.created_at)).offset(offset).limit(limit)
    )
    product_masters = db.exec(statement).all()
    return list(product_masters), total


def create_product_master(db: Session, product_master: ProductMaster):
    db.add(product_master)
    db.commit()
    db.refresh(product_master)
    return product_master


def update_product_master(db: Session, product_master: ProductMaster):
    db.add(product_master)
    db.commit()
    db.refresh(product_master)
    return product_master


def delete_product_master(db: Session, product_master: ProductMaster):
    # Soft delete product master and cascade soft delete to related combos per rules
    from apps.products.exceptions import product_delete_blocked_active_sales
    from apps.products.models import ComboProduct

    # Find all combos containing this product master
    combo_products = db.exec(
        select(ComboProduct).where(ComboProduct.product_master_id == product_master.id)
    ).all()
    affected_combo_ids = {cp.combo_id for cp in combo_products}

    # Load combos
    combos = []
    if affected_combo_ids:
        combos = db.exec(select(Combo).where(Combo.id.in_(affected_combo_ids))).all()

    now = get_current_time()
    # Check if any combo is actively selling (listing_end_date > now) → block delete
    for c in combos:
        if (
            c.is_available
            and c.status == COMBO_STATUS_SELLING
            and c.listing_end_date
            and c.listing_end_date > now
        ):
            raise product_delete_blocked_active_sales()

    # Otherwise soft delete the product master
    product_master.is_active = False
    product_master.updated_at = now
    db.add(product_master)

    # Soft delete all affected combos (expired or sold/finished) that contain this product master
    for c in combos:
        if c.is_available:
            c.is_available = False
            c.updated_at = now
            db.add(c)

    db.commit()


def get_foodloss_grams_by_combo_ids(db: Session, combo_ids: list) -> float:
    """Sum food_waste_weight * quantity for all combo products in the given combo IDs"""
    if not combo_ids:
        return 0.0
    rows = db.exec(
        select(ComboProduct.quantity, ProductMaster.food_waste_weight)
        .join(ProductMaster, ComboProduct.product_master_id == ProductMaster.id)
        .where(ComboProduct.combo_id.in_(combo_ids))
    ).all()
    return sum((food_waste_weight or 0) * quantity for quantity, food_waste_weight in rows)


def get_combo_locker_reservation(db: Session, combo_id: str):
    """Get the locker reservation associated with a combo"""
    return db.exec(
        select(LockerReservation).where(LockerReservation.combo_id == combo_id)
    ).first()


def get_locker_reservation_by_unit(db: Session, locker_unit_id: str):
    return db.exec(
        select(LockerReservation).where(
            LockerReservation.locker_unit_id == locker_unit_id
        )
    ).first()


def get_combo_locker_unit_with_location(db: Session, combo_id: str):
    """Get the locker unit and location information for a combo"""
    from apps.lockers.models.location import LockerLocation
    from apps.lockers.models.reservation import LockerReservation
    from apps.lockers.models.unit import LockerUnit

    # Join reservation -> unit -> location following the existing pattern
    statement = (
        select(LockerUnit, LockerLocation, LockerReservation)
        .join(LockerReservation)
        .join(LockerLocation)
        .where(
            LockerReservation.combo_id == combo_id,
            LockerReservation.locker_unit_id == LockerUnit.id,
            LockerUnit.location_id == LockerLocation.id,
        )
    )

    result = db.exec(statement).first()
    return result
