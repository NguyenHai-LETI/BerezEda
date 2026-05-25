from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException
from sqlmodel import Session

from apps.core.schemas import DEFAULT_LIMIT, DEFAULT_OFFSET
from apps.favorites import crud as favorite_crud
from apps.lockers.crud import get_locker_location_by_id
from apps.lockers.exceptions import locker_location_not_found
from apps.shops import crud, schemas
from apps.shops.crud import update_shop
from apps.shops.exceptions import shop_not_found, unauthorized_shop_removal
from apps.shops.models.shops import Shop
from apps.shops.schemas import SalesHistoryRead
from apps.shops.utils import (
    convert_multiple_shops_to_schema,
    convert_single_shop_to_schema,
    generate_shop_code,
)
from apps.users import crud as user_crud
from apps.users.models.users import User


def get_shop_priority(shop_data) -> int:
    """
    Get priority value for shop sorting.

    Priority order:
    1. is_favorite = True AND has_selling_combos = True
    2. is_favorite = True AND has_selling_combos = False
    3. is_favorite = False AND has_selling_combos = True
    4. is_favorite = False AND has_selling_combos = False

    Args:
        shop_data: ShopReadWithDistance object

    Returns:
        Priority value (1-4, lower is higher priority)
    """
    if shop_data.is_favorite and shop_data.has_selling_combos:
        return 1
    elif shop_data.is_favorite and not shop_data.has_selling_combos:
        return 2
    elif not shop_data.is_favorite and shop_data.has_selling_combos:
        return 3
    else:
        return 4


def get_shop_service(shop_id: str, user: Optional[User], db: Session):
    shop = crud.get_shop(db, shop_id)
    if not shop:
        raise shop_not_found()

    user_id = user.id if user else None
    shop_data = convert_single_shop_to_schema(shop, user_id, db)

    # Get owner email
    if shop.owner_id:
        owner_user = user_crud.get_user(db, shop.owner_id)
        if owner_user:
            shop_data.owner_email = owner_user.email

    return shop_data


def get_my_shop_service(user: User, db: Session):
    """Get the shop associated with the current user using direct relationship."""
    user_shop = user.get_associated_shop()
    if not user_shop:
        raise shop_not_found()

    return convert_single_shop_to_schema(user_shop, user.id, db)


def list_shops_service(
    user: User,
    db: Session,
    limit: int = DEFAULT_LIMIT,
    offset: int = DEFAULT_OFFSET,
    name: Optional[str] = None,
):
    shops, total = crud.get_shops(db, limit, offset, name)
    result_shops = convert_multiple_shops_to_schema(shops, user.id, db)
    return result_shops, total


def create_shop_service(shop: schemas.ShopCreate, user: User, db: Session):
    """Create a shop and return the schema."""
    code = generate_shop_code(db)

    shop_data = shop.model_dump()
    shop_data["code"] = code

    new_shop = Shop(**shop_data)
    new_shop = crud.create_shop(db, new_shop)

    # Sync to Firebase asynchronously
    from apps.shops.tasks import sync_shop_to_firebase_task

    sync_shop_to_firebase_task(str(new_shop.id))

    # New shop won't be favorited yet, so we can optimize this
    shop_data = schemas.ShopRead.model_validate(new_shop, from_attributes=True)
    shop_data.is_favorite = False
    return shop_data


def delete_shop_service(shop_id: str, db: Session, user: User):
    if user.permissions == "admin":
        pass
    elif user.permissions == "owner_shop":
        user_shop = user.get_associated_shop()
        if not user_shop or str(shop_id) != str(user_shop.id):
            raise unauthorized_shop_removal()
    shop = crud.get_shop(db, shop_id)
    if not shop:
        raise shop_not_found()

    # Soft delete all users associated with this shop
    user_crud.delete_users_by_shop_code(db, shop.code)

    crud.delete_shop(db, shop)

    # Delete from Firebase asynchronously
    from apps.shops.tasks import delete_shop_from_firebase_task

    delete_shop_from_firebase_task(str(shop_id))

    return None


def update_shop_contact_service(
    shop_update: schemas.ShopPartialUpdate, user, db: Session
):
    """Update only phone and description fields of the current user's shop"""
    user_shop = user.get_associated_shop()
    if not user_shop:
        raise shop_not_found()

    shop = user_shop

    if user.role != "owner_shop":
        raise unauthorized_shop_removal()

    update_data = shop_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(shop, field):
            setattr(shop, field, value)

    updated_shop = update_shop(db, shop)
    return convert_single_shop_to_schema(updated_shop, user.id, db)


def sync_all_shops_analytics_to_firebase(db: Session):
    """Sync analytics for all active shops to Firebase."""
    from apps.shops.tasks import sync_shop_analytics_to_firebase_task

    shops = crud.get_all_active_shops(db)
    for shop in shops:
        sync_shop_analytics_to_firebase_task.delay(str(shop.id))

    return len(shops)


def get_shop_combos_service(
    shop_id: str,
    db: Session,
    user,
    limit: int = DEFAULT_LIMIT,
    offset: int = DEFAULT_OFFSET,
    is_selling: Optional[bool] = None,
):
    """
    Get all combos for a specific shop with filtering and ordering logic.
    """
    # Verify shop exists
    shop = crud.get_shop(db, shop_id)
    if not shop:
        raise shop_not_found()

    # Get combos from CRUD (already enriched with calculated fields)
    combo_data, total = crud.get_combo_shop(
        db, shop_id, is_selling, offset, limit, user=user
    )

    return combo_data, total


def get_shop_sales_history_service(
    shop_id: str, date: str, user: User, db: Session, limit: int = 20, offset: int = 0
) -> tuple[List[SalesHistoryRead], int]:
    """Get sales history for a shop with filters applied"""

    from apps.products.schemas import LockerLocationBasic, LockerUnitRead

    # Parse the date filter
    filter_date = None
    if date:
        try:
            # Parse the date in format YYYY-MM-DD
            filter_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid date format. Use YYYY-MM-DD format."
            )

    # Verify shop exists
    shop = crud.get_shop(db, shop_id)
    if not shop:
        raise shop_not_found()

    # Get the raw sales history data
    sales_data = crud.get_shop_sales_history(db, shop_id, filter_date)

    # Get total count before pagination
    total = len(sales_data)

    # Apply pagination
    paginated_data = sales_data[offset : offset + limit]

    # Convert to response schema
    sales_history = []
    for item in paginated_data:
        # Build locker_unit field from the data
        locker_unit = None
        if item.get("locker_unit"):
            unit = item["locker_unit"]
            reservation = item.get("reservation")

            # Build location if available
            location = None
            if unit.location:
                location = LockerLocationBasic(
                    id=unit.location.id,
                    name=unit.location.name,
                    address=unit.location.address,
                    description=unit.location.description,
                    code=unit.location.code,
                    position=unit.location.position,
                )

            # Build locker unit with access code from reservation and preparation deadline
            locker_unit = LockerUnitRead(
                id=unit.id,
                unit_number=unit.unit_number,
                status=unit.status,
                size=unit.size,
                access_code=reservation.access_code if reservation else None,
                location=location,
                preparation_deadline=(
                    reservation.preparation_deadline if reservation else None
                ),
            )

        sales_history_item = SalesHistoryRead(
            sales_end_date=item["sales_end_date"],
            status=item["status"],
            combo_id=item["combo_id"],
            locker_unit=locker_unit,
            combo_name=item["combo_name"],
            product_number=item["product_number"],
            is_free=item["is_free"],
            order=item["order"],
        )
        sales_history.append(sales_history_item)

    return sales_history, total


def get_shops_by_location_service(
    location_id: str,
    user: Optional[User],
    db: Session,
    limit: int = DEFAULT_LIMIT,
    offset: int = DEFAULT_OFFSET,
):
    """
    Get shops that have sold at least 1 combo at the specified locker location.

    Args:
        location_id: ID of the locker location
        user: Optional authenticated user
        db: Database session
        limit: Number of items per page
        offset: Number of items to skip

    Returns:
        Tuple of (list of ShopReadWithDistance objects, total count)
    """
    # Verify location exists
    location = get_locker_location_by_id(db, location_id)
    if not location:
        raise locker_location_not_found()

    # Get shops and selling combos count from CRUD
    shops, total, selling_combos_count = crud.get_shops_by_location_id(
        db, location_id, limit=limit, offset=offset
    )

    if not shops:
        return [], total

    # Batch query for favorites
    user_id = user.id if user else None
    shop_ids = [shop.id for shop in shops]
    favorited_shop_ids = set()
    if user_id:
        user_favorites = favorite_crud.get_favorites_by_user_and_shops(
            db, user_id, shop_ids
        )
        favorited_shop_ids = {fav.shop_id for fav in user_favorites}

    # Convert to ShopReadWithDistance
    result_shops = []
    for shop in shops:
        shop_data = schemas.ShopReadWithDistance.model_validate(
            shop, from_attributes=True
        )
        combo_count = selling_combos_count.get(str(shop.id), 0)
        shop_data.is_favorite = shop.id in favorited_shop_ids
        shop_data.distance = None
        shop_data.number_combos = combo_count
        shop_data.has_selling_combos = combo_count > 0
        result_shops.append(shop_data)

    # Sort by priority
    result_shops.sort(key=get_shop_priority)

    return result_shops, total
