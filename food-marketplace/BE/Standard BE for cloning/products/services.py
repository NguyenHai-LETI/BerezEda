from datetime import datetime, timedelta
from typing import List, Optional, Union, cast

from sqlmodel import Session

from apps.auth.permissions import can_manage_shop_products
from apps.core.constants import (
    COMBO_STATUS_DELETED,
    COMBO_STATUS_DRAFT,
    COMBO_STATUS_EXPIRED,
    COMBO_STATUS_PREPARATION_TO_LOCKER,
    COMBO_STATUS_SELLING,
    COMBO_STATUS_SOLD,
    RESERVATION_STATUS_COMPLETED,
    UNIT_STATUS_AVAILABLE,
)
from apps.core.utils import get_current_time, get_distance
from apps.favorites.crud import get_favorite_by_user_and_shop
from apps.lockers.crud import (
    get_locker_reservation_by_unit_and_shop,
    get_locker_reservations_by_combo_id,
    get_locker_unit_by_id,
    update_locker_reservation,
    update_locker_unit,
)
from apps.lockers.exceptions import locker_reservation_not_found
from apps.lockers.tasks import sync_location_to_firebase_task
from apps.orders.crud import get_order_by_combo
from apps.orders.schemas import OrderRead
from apps.products import validators
from apps.products.validators import validate_locker_unit_availability_for_relisting
from apps.users.models import User

# Legacy constants for backward compatibility - TODO: Remove this
COMBO_STATUS_FREE_FOR_NEEDY = "FREE_FOR_NEEDY"  # Not in current spec
from apps.products.crud import (
    create_combo,
    create_combo_product,
    create_product_master,
    delete_combo,
    delete_combo_products,
    delete_product_master,
    get_combo_by_id,
    get_combo_locker_reservation,
    get_combo_locker_unit_with_location,
    get_combo_products_by_product_master,
    get_combo_with_product_masters,
    get_combo_with_products,
    get_combos,
    get_product_master,
    get_product_master_by_name_and_shop,
    get_product_masters,
    get_public_combos,
    update_combo,
    update_product_master,
)
from apps.products.exceptions import (
    combo_already_sold_cannot_cancel,
    combo_cannot_cancel_invalid_status,
    combo_has_been_purchased,
    combo_not_belong_to_shop,
    combo_not_found,
    combo_products_update_forbidden,
    combo_update_not_allowed,
    draft_already_deleted,
    draft_already_sale_registered,
    locker_unit_id_required,
    product_already_exists,
    product_master_already_deleted,
    product_master_not_found,
    shop_management_required,
)
from apps.products.models import Combo, ComboProduct, ProductMaster
from apps.products.schemas import (
    ComboCreate,
    ComboDraftCreate,
    ComboEdit,
    ComboFlattenedRead,
    ComboListRead,
    ComboPreview,
    ComboProductFlattened,
    ComboRead,
    ComboUpdate,
    LockerLocationBasic,
    LockerUnitRead,
    ProductDetailPreview,
    ProductMasterCreate,
    ProductMasterRead,
    ProductMasterUpdate,
    ShopBasicRead,
)
from apps.products.utils import (
    count_shop_pending_combos,
    enrich_combo_with_calculated_fields,
    parse_sales_duration_to_seconds,
    sync_shop_combo_count_to_firebase,
)
from apps.shops.crud import get_shop
from apps.shops.exceptions import shop_not_found


def _convert_combo_to_list_read(
    combo: Combo, db: Session, user: Optional[User] = None
) -> ComboListRead:
    """Convert Combo model to ComboListRead schema with additional fields populated"""
    combo_data = ComboListRead.model_validate(combo, from_attributes=True)

    # Use utility function to populate all calculated fields
    enrich_combo_with_calculated_fields(combo_data, combo, db, user)

    # Calculate foodloss and CO2 reduction
    foodloss_grams = sum(
        (cp.product_master.food_waste_weight or 0) * cp.quantity
        for cp in combo.combo_products
        if cp.product_master
    )
    combo_data.foodloss = round(foodloss_grams / 1000, 4)
    combo_data.co2_reduction = round(combo_data.foodloss * 2.5, 4)

    return combo_data


def get_combo_service(combo_id: str, user, db: Session):
    """Get combo with flattened product information, shop details, and locker info"""
    combo = get_combo_with_product_masters(db, combo_id)
    if combo is None or (
        user is not None
        and user.role != "owner_shop"
        and combo.status == COMBO_STATUS_DELETED
    ):
        raise combo_not_found()

    # Create flattened products list using the class method
    flattened_products = []
    for combo_product in combo.combo_products:
        try:
            flattened_product = ComboProductFlattened.from_combo_product(combo_product)
            flattened_products.append(flattened_product)
        except Exception as e:
            print(f"[ERROR] Failed to process combo_product {combo_product.id}: {e}")
            continue

    # Create shop information with favorite status
    shop_data = None
    if combo.shop:
        is_favorite = False
        if user:
            favorite = get_favorite_by_user_and_shop(db, user.id, combo.shop.id)
            is_favorite = favorite is not None

        shop_data = ShopBasicRead(
            id=combo.shop.id,
            name=combo.shop.name,
            description=combo.shop.description,
            avg_rating=combo.shop.avg_rating,
            total_reviews=combo.shop.total_reviews,
            is_favorite=is_favorite,
        )

    # Get locker information for this combo
    locker_unit_data = _get_combo_locker_info(db, combo_id)
    # Create combo response using model_validate and enrich calculated fields
    combo_with_products = get_combo_with_products(db, combo_id)
    # Build validated ComboRead-like object then enrich
    order = get_order_by_combo(db, combo_id) or None
    order_data = None
    if order:
        order_user = db.get(User, order.user_id)
        order_data = OrderRead.build(order, user_obj=order_user)

    # Calculate foodloss and CO2 reduction
    foodloss_grams = sum(
        (p.food_waste_weight or 0) * p.quantity for p in flattened_products
    )
    foodloss_kg = round(foodloss_grams / 1000, 4)
    co2_reduction_kg = round(foodloss_kg * 2.5, 4)

    combo_data = ComboFlattenedRead.model_validate(
        {
            **{
                k: v
                for k, v in combo_with_products.__dict__.items()
                if k != "_sa_instance_state"
            },
            "products": flattened_products,
            "shop": shop_data,
            "locker_unit": locker_unit_data,
            "order": order_data,
            "foodloss": foodloss_kg,
            "co2_reduction": co2_reduction_kg,
        }
    )

    # Enrich calculated fields (timing, pricing, shop, locker)
    if combo_with_products is None:
        raise combo_not_found()
    enrich_combo_with_calculated_fields(combo_data, combo_with_products, db, user)

    return combo_data


def _get_combo_locker_info(db: Session, combo_id: str):
    """Get locker unit and location information for a combo"""
    # Use the CRUD function following the project structure
    result = get_combo_locker_unit_with_location(db, combo_id)

    if not result:
        return None

    unit, location, reservation = result
    # Create unit data with nested location structure for LockerUnitRead
    location_data = LockerLocationBasic.model_validate(location, from_attributes=True)

    unit_data = LockerUnitRead(
        id=unit.id,
        unit_number=unit.unit_number,
        status=unit.status,
        size=unit.size,
        access_code=reservation.access_code if reservation else None,
        location=location_data,
        preparation_deadline=reservation.preparation_deadline if reservation else None,
        locker_reservation_id=reservation.id if reservation else None,
    )

    return unit_data


def list_combos_service(
    db: Session,
    user=None,
    limit: int = 20,
    offset: int = 0,
    is_draft: Optional[bool] = None,
):
    combos, total = get_combos(
        db, user=user, limit=limit, offset=offset, is_draft=is_draft
    )
    return [
        ComboListRead.model_validate(c, from_attributes=True) for c in combos
    ], total


def list_public_combos_service(
    db: Session,
    user=None,
    limit: int = 20,
    offset: int = 0,
    shop_id: Optional[str] = None,
    category: Optional[str] = None,
    user_lat: Optional[str] = None,
    user_lng: Optional[str] = None,
    distance: Optional[float] = None,
):
    """Get publicly available combos for customers"""
    # Only create user_location if both lat and lng are provided
    user_location = None
    if user_lat and user_lng:
        user_location = f"{user_lat},{user_lng}"
    combos, total = get_public_combos(
        db,
        limit=limit,
        offset=offset,
        shop_id=shop_id,
        category=category,
        include_sold_out=True,
    )

    # Filter out free combos for users without MyNa Portal linking
    if user and hasattr(user, "my_portal"):
        if user.my_portal != "linked":
            # Filter out free_for_needy combos
            combos = [c for c in combos if c.status != COMBO_STATUS_FREE_FOR_NEEDY]
            # Recalculate total without free combos
            all_combos, _ = get_public_combos(
                db,
                limit=1000,
                offset=0,
                shop_id=shop_id,
                category=category,
            )
            filtered_combos = [
                c for c in all_combos if c.status != COMBO_STATUS_FREE_FOR_NEEDY
            ]
            total = len(filtered_combos)

    # Enrich distance here to avoid mutating ORM model (Combo has no 'distance' field)
    enriched_list = []
    for c in combos:
        data = _convert_combo_to_list_read(c, db, user)
        result = get_combo_locker_unit_with_location(db, c.id)
        if result:
            _, location, _ = result
            if user_location and not "None" in user_location and location.position:
                data.distance = get_distance(user_location, location.position)
                if distance and data.distance < distance:
                    enriched_list.append(data)
                elif not distance:
                    enriched_list.append(data)
            else:
                # Set distance to None when user location is not provided
                data.distance = None
                # Don't filter by distance when user location is not provided
                enriched_list.append(data)
        else:
            # No locker unit found, set distance to None
            data.distance = None
            # Don't filter by distance when user location is not provided
            enriched_list.append(data)

    # Sort SELLING combos by soonest expiry (least remaining time first)
    # Preserve non-SELLING ordering after SELLING group
    enriched_list.sort(
        key=lambda combo: (
            combo.status != COMBO_STATUS_SELLING,
            (
                combo.time_remaining_seconds
                if combo.time_remaining_seconds is not None
                else 10**12
            ),
        )
    )

    total = len(enriched_list)
    return enriched_list, total


def list_combos_by_locker_location_service(
    db: Session,
    location_id: str,
    user=None,
    limit: int = 20,
    offset: int = 0,
    category: Optional[str] = None,
    is_selling: Optional[bool] = None,
):
    """Get all combos available in a specific locker location"""
    from apps.lockers.crud import (
        get_favorite_locker_by_user_and_location,
        update_favorite_locker_last_used_at,
    )
    from apps.products.crud import get_combos_by_locker_location

    # Update last_used_at if this location is in the authenticated user's favorites
    if user and hasattr(user, "id"):
        favorite = get_favorite_locker_by_user_and_location(db, user.id, location_id)
        if favorite:
            update_favorite_locker_last_used_at(db, favorite)

    combos, total = get_combos_by_locker_location(
        db,
        location_id=location_id,
        limit=limit,
        offset=offset,
        category=category,
        is_selling=is_selling,
    )

    # Filter out free combos for users without MyNa Portal linking
    if user and hasattr(user, "my_portal"):
        if user.my_portal != "linked":
            # Filter out free_for_needy combos
            combos = [c for c in combos if c.status != COMBO_STATUS_FREE_FOR_NEEDY]
            # Recalculate total without free combos
            all_combos, _ = get_combos_by_locker_location(
                db,
                location_id=location_id,
                limit=1000,
                offset=0,
                category=category,
            )
            filtered_combos = [
                c for c in all_combos if c.status != COMBO_STATUS_FREE_FOR_NEEDY
            ]
            total = len(filtered_combos)

    return [_convert_combo_to_list_read(c, db, user) for c in combos], total


def preview_combo_service(combo: ComboCreate, user, db: Session):
    """Preview combo creation with calculated prices and validation"""
    # case upgrade from draft in app
    if combo.combo_id:
        combo_in_db = get_combo_by_id(db, combo.combo_id)
        if not combo_in_db:
            raise draft_already_deleted()
        if not combo_in_db.is_draft:
            raise draft_already_sale_registered()

    # Validate shop exists
    shop = get_shop(db, combo.shop_id)
    if not shop:
        raise shop_not_found()

    # Check permissions
    if not can_manage_shop_products(user, combo.shop_id, db):
        raise shop_management_required()

    # Calculate prices and gather product details
    total_price = 0.0
    product_details = []

    for product_item in combo.products:
        product_master = get_product_master(db, product_item.product_master_id)
        if not product_master:
            raise product_master_not_found()

        total_price += product_master.selling_price * product_item.quantity

        # Create product detail with master info plus combo-specific info
        product_master_dict = product_master.__dict__.copy()
        product_master_dict["quantity"] = product_item.quantity
        product_master_dict["expiry_dates"] = product_item.expiry_dates

        product_details.append(
            ProductDetailPreview.model_validate(
                product_master_dict, from_attributes=True
            )
        )

    # Calculate final price after discount
    discount_amount = (total_price * combo.discount_percentage) / 100
    final_price = total_price - discount_amount

    # Create shop information with favorite status
    shop_data = None
    if shop:
        # Check if shop is favorite for current user
        is_favorite = False
        if user:
            favorite = get_favorite_by_user_and_shop(db, user.id, shop.id)
            is_favorite = favorite is not None

        shop_data = ShopBasicRead(
            id=shop.id,
            name=shop.name,
            description=shop.description,
            avg_rating=shop.avg_rating or 0.0,
            total_reviews=shop.total_reviews or 0,
            is_favorite=is_favorite,
        )

    # Create locker information if locker_unit_id is provided
    locker_data = None
    if combo.locker_unit_id:
        locker_unit = get_locker_unit_by_id(db, combo.locker_unit_id)
        if locker_unit and locker_unit.location:
            # Try to get reservation for this unit and shop to get access_code
            from apps.lockers.crud import get_locker_reservation_by_unit_and_shop

            # Get shop_id for the reservation lookup
            shop_id = combo.shop_id
            reservation = get_locker_reservation_by_unit_and_shop(
                db, combo.locker_unit_id, shop_id
            )

            # Create nested location object
            location_data = LockerLocationBasic(
                id=locker_unit.location.id,
                name=locker_unit.location.name,
                address=locker_unit.location.address,
                description=locker_unit.location.description,
                code=locker_unit.location.code,
                position=locker_unit.location.position,
            )
            locker_data = LockerUnitRead(
                id=locker_unit.id,
                unit_number=locker_unit.unit_number,
                status=locker_unit.status,
                size=locker_unit.size,
                access_code=reservation.access_code if reservation else None,
                location=location_data,
                preparation_deadline=(
                    reservation.preparation_deadline if reservation else None
                ),
                locker_reservation_id=reservation.id if reservation else None,
            )

    # Create preview response
    preview_data = {
        "name": combo.name,
        "description": combo.description,
        "images": combo.images or [],
        "is_available": combo.is_available,
        "original_price": total_price,
        "discount_percentage": combo.discount_percentage,
        "final_price": final_price,
        "category": combo.category,
        "listing_end_date": combo.listing_end_date,
        "pickup_deadline": combo.pickup_deadline,
        "sales_duration": combo.sales_duration,
        "is_free": combo.is_free,
        "is_draft": combo.is_draft,
        "is_checked": combo.is_checked,
        "shop": shop_data,
        "locker_unit": locker_data,
        "product_details": product_details,
        "total_products": len(combo.products),
    }

    return ComboPreview.model_validate(preview_data)


def create_combo_service(combo: ComboCreate, user, db: Session):
    shop = get_shop(db, combo.shop_id)
    if not shop:
        raise shop_not_found()

    if not can_manage_shop_products(user, combo.shop_id, db):
        raise shop_management_required()

    status = COMBO_STATUS_DRAFT
    # Validate locker reservation if locker_unit_id is provided
    locker_reservation = None
    if combo.locker_unit_id:
        status = COMBO_STATUS_PREPARATION_TO_LOCKER
        locker_reservation = get_locker_reservation_by_unit_and_shop(
            db, combo.locker_unit_id, combo.shop_id
        )
        if not locker_reservation:
            raise locker_reservation_not_found()

    total_price = 0.0
    for product_item in combo.products:
        product_master = get_product_master(db, product_item.product_master_id)
        if not product_master:
            raise product_master_not_found()
        total_price += product_master.selling_price * product_item.quantity

    combo_data = combo.model_dump(exclude={"products"})
    combo_data["original_price"] = total_price
    combo_data["status"] = status

    # TODO : improve product_number generation logic
    import time

    combo_data["product_number"] = f"COMBO_{int(time.time())}"

    # Set edited_at when creating new combo
    combo_data["edited_at"] = get_current_time()

    new_combo = Combo(**combo_data)
    new_combo = create_combo(db, new_combo)

    for product_item in combo.products:
        combo_product = ComboProduct(
            combo_id=new_combo.id,
            product_master_id=product_item.product_master_id,
            quantity=product_item.quantity,
            expiry_dates=cast(
                Optional[List[Union[datetime, str]]], product_item.expiry_dates or []
            ),
        )
        create_combo_product(db, combo_product)

    # Update locker reservation with combo_id if locker was selected
    if locker_reservation:
        update_locker_reservation(db, locker_reservation.id, {"combo_id": new_combo.id})

        # Generate access code for the locker unit when combo is created
        import os

        from apps.lockers.crud import get_locker_unit_by_id
        from apps.lockers.services import generate_access_code_service
        from apps.lockers.utils import generate_access_code_in, generate_and_save_qr_code_url

        locker_unit = get_locker_unit_by_id(db, combo.locker_unit_id)

        if os.getenv("GALILEI_MODE") == "0":
            # Generate access code via Galilei API
            access_code = generate_access_code_service(locker_unit, put_in=True)[2:]
        else:
            # Generate access code locally (test mode)
            access_code = generate_access_code_in()[2:]

        # Update reservation with the generated access code
        update_locker_reservation(
            db, locker_reservation.id, {"access_code": access_code}
        )

        # Generate QR code once and cache URL in DB
        db.refresh(locker_reservation)
        generate_and_save_qr_code_url(locker_reservation, db)

    # Retrieve combo with relationships for response
    combo_with_products = get_combo_with_products(db, new_combo.id)

    if not combo_with_products:
        raise combo_not_found()

    # Check and update Firebase shop combo count if criteria are met
    combo_count = count_shop_pending_combos(db, combo.shop_id)
    sync_shop_combo_count_to_firebase(combo.shop_id, combo_count)

    # Convert to ComboRead with all calculated fields
    combo_data = ComboRead.model_validate(combo_with_products, from_attributes=True)

    # Use utility function to populate all calculated fields (timing, pricing, shop, locker)
    enrich_combo_with_calculated_fields(combo_data, combo_with_products, db)

    return combo_data


def save_combo_draft_service(combo: ComboDraftCreate, user, db: Session):
    """Save combo as draft without strict validation - allows incomplete data"""
    shop = get_shop(db, combo.shop_id)
    if not shop:
        raise shop_not_found()

    if not can_manage_shop_products(user, combo.shop_id, db):
        raise shop_management_required()

    # For drafts, always use DRAFT status
    status = COMBO_STATUS_DRAFT

    # Calculate price only if products are provided
    total_price = 0.0
    if combo.products:
        for product_item in combo.products:
            product_master = get_product_master(db, product_item.product_master_id)
            if product_master:
                total_price += product_master.selling_price * product_item.quantity

    combo_data = combo.model_dump(exclude={"products"})
    combo_data["original_price"] = total_price
    combo_data["status"] = status
    combo_data["is_draft"] = True

    # TODO : improve product_number generation logic
    import time

    combo_data["product_number"] = f"DRAFT_{int(time.time())}"

    # Set edited_at when creating new combo
    combo_data["edited_at"] = get_current_time()

    new_combo = Combo(**combo_data)
    new_combo = create_combo(db, new_combo)

    # Add products only if they exist and are valid
    if combo.products:
        for product_item in combo.products:
            product_master = get_product_master(db, product_item.product_master_id)
            if product_master:
                combo_product = ComboProduct(
                    combo_id=new_combo.id,
                    product_master_id=product_item.product_master_id,
                    quantity=product_item.quantity,
                    expiry_dates=cast(
                        Optional[List[Union[datetime, str]]], product_item.expiry_dates
                    ),
                )
                create_combo_product(db, combo_product)

    # Retrieve combo with relationships for response
    combo_with_products = get_combo_with_products(db, new_combo.id)

    if not combo_with_products:
        raise combo_not_found()

    # Convert to ComboRead with all calculated fields
    combo_data = ComboRead.model_validate(combo_with_products, from_attributes=True)

    # Use utility function to populate all calculated fields (timing, pricing, shop, locker)
    enrich_combo_with_calculated_fields(combo_data, combo_with_products, db)

    return combo_data


def update_combo_service(combo_id: str, update: ComboUpdate, user, db: Session):
    combo = get_combo_by_id(db, combo_id)
    if not combo:
        raise draft_already_deleted()

    if not combo.is_draft:
        # case staff upgrade draft to public, but its already public
        # case staff update draft information, but its already public
        raise draft_already_sale_registered()

    if not can_manage_shop_products(user, combo.shop_id, db):
        raise shop_management_required()

    # Get the list of fields being updated
    update_dict = update.model_dump(exclude_unset=True)
    update_fields = list(update_dict.keys())

    # Validate if combo can be updated with these fields
    is_valid, error_message = validators.validate_combo_for_update(
        combo, update_fields, update_dict
    )
    if not is_valid:
        raise combo_update_not_allowed(error_message)

    # Special check for products field when combo is sold
    if update.products is not None and combo.status == COMBO_STATUS_SOLD:
        raise combo_products_update_forbidden()

    if update.products is not None:
        delete_combo_products(db, combo_id)

        total_price = 0.0
        for product_item in update.products:
            product_master = get_product_master(db, product_item.product_master_id)
            if not product_master:
                raise product_master_not_found()
            total_price += product_master.selling_price * product_item.quantity

        combo.original_price = total_price

        for product_item in update.products:
            combo_product = ComboProduct(
                combo_id=combo_id,
                product_master_id=product_item.product_master_id,
                quantity=product_item.quantity,
                expiry_dates=cast(
                    Optional[List[Union[datetime, str]]], product_item.expiry_dates
                ),
            )
            create_combo_product(db, combo_product)

    for field, value in update.model_dump(
        exclude_unset=True, exclude={"products", "locker_unit_id"}
    ).items():
        setattr(combo, field, value)

    # Update locker reservation with combo_id if locker was selected
    if update.locker_unit_id and update.is_draft is False:
        # Look for reservation specific to this shop and unit
        locker_reservation = get_locker_reservation_by_unit_and_shop(
            db, update.locker_unit_id, combo.shop_id
        )
        if locker_reservation:
            update_locker_reservation(db, locker_reservation.id, {"combo_id": combo.id})
        else:
            raise locker_reservation_not_found()

        # Generate access code for the locker unit when combo is published
        import os

        from apps.lockers.crud import get_locker_unit_by_id
        from apps.lockers.services import generate_access_code_service
        from apps.lockers.utils import generate_access_code_in, generate_and_save_qr_code_url

        locker_unit = get_locker_unit_by_id(db, update.locker_unit_id)

        if os.getenv("GALILEI_MODE") == "0":
            # Generate access code via Galilei API
            access_code = generate_access_code_service(locker_unit, put_in=True)[2:]
        else:
            # Generate access code locally (test mode)
            access_code = generate_access_code_in()[2:]

        # Update reservation with the generated access code
        update_locker_reservation(
            db, locker_reservation.id, {"access_code": access_code}
        )

        # Generate QR code once and cache URL in DB
        db.refresh(locker_reservation)
        generate_and_save_qr_code_url(locker_reservation, db)

        combo.status = COMBO_STATUS_PREPARATION_TO_LOCKER
        combo.updated_at = get_current_time()
        combo = update_combo(db, combo)

    elif not update.is_draft:
        # case update draft to public required locker unit id
        raise locker_unit_id_required()

    else:
        # Save changes to database for other updates
        combo = update_combo(db, combo)

    # Return the same detailed response as get_combo_service
    return get_combo_service(combo_id, user, db)


def edit_combo_service(combo_id: str, update: ComboEdit, user, db: Session):
    """
    Edit combo information - simplified version that only updates specific fields.
    Updates: images, name, description, is_free, discount_percentage,
    products, is_draft, locker_unit_id, sales_duration
    Calculates listing_end_date from sales_duration if provided.

    Supports editing both SELLING and EXPIRED combos.
    When editing EXPIRED combo with new sales_duration, it will be re-listed as SELLING.
    """
    from apps.core.logging import logger
    from apps.integrations.redis.lock import redis_lock

    # Use Redis distributed lock to prevent race condition with purchase
    logger.info(f"Attempting to acquire lock for combo edit: {combo_id}")
    with redis_lock(f"combo:{combo_id}", timeout=10, blocking_timeout=5):
        logger.info(f"Lock acquired for combo edit: {combo_id}")

        # Get fresh combo data from DB after acquiring lock
        combo = get_combo_by_id(db, combo_id)
        if not combo:
            raise combo_not_found()
        if combo.status == COMBO_STATUS_SOLD:
            logger.warning(f"Combo {combo_id} already sold, cannot edit")
            raise combo_has_been_purchased()

        # Track if this is an expired combo being re-listed
        is_relisting_expired = combo.status == COMBO_STATUS_EXPIRED

        if not can_manage_shop_products(user, combo.shop_id, db):
            raise shop_management_required()

        # Validate locker unit status for re-listing expired combo
        if is_relisting_expired and update.sales_duration is not None:
            validate_locker_unit_availability_for_relisting(db, combo_id, logger)

        # Update products if provided
        if update.products is not None:
            delete_combo_products(db, combo_id)

            total_price = 0.0
            for product_item in update.products:
                product_master = get_product_master(db, product_item.product_master_id)
                if not product_master:
                    raise product_master_not_found()
                total_price += product_master.selling_price * product_item.quantity

            combo.original_price = total_price

            for product_item in update.products:
                combo_product = ComboProduct(
                    combo_id=combo_id,
                    product_master_id=product_item.product_master_id,
                    quantity=product_item.quantity,
                    expiry_dates=cast(
                        Optional[List[Union[datetime, str]]], product_item.expiry_dates
                    ),
                )
                create_combo_product(db, combo_product)

        # Calculate listing_end_date from sales_duration if provided
        # For EXPIRED combos: always update listing_end_date to re-list
        # For SELLING combos: only update if sales_duration value has changed
        if update.sales_duration is not None:
            old_sales_duration = combo.sales_duration
            new_sales_duration = update.sales_duration

            # Update if: value changed OR combo is expired (re-listing)
            should_update_duration = (
                old_sales_duration != new_sales_duration or is_relisting_expired
            )

            if should_update_duration:
                duration_seconds = parse_sales_duration_to_seconds(
                    update.sales_duration
                )
                current_time = get_current_time()
                combo.listing_end_date = current_time + timedelta(
                    seconds=duration_seconds
                )
                # Also update sales_duration field
                combo.sales_duration = update.sales_duration

                # If re-listing expired combo, change status back to SELLING
                if is_relisting_expired:
                    combo.status = COMBO_STATUS_SELLING
                    logger.info(
                        f"Re-listing expired combo {combo_id} as SELLING, "
                        f"new listing_end_date: {combo.listing_end_date}"
                    )

                # Update sale_end_time in locker_reservation
                locker_reservation = get_locker_reservations_by_combo_id(db, combo_id)
                if locker_reservation:
                    new_sale_end_time = current_time + timedelta(
                        seconds=duration_seconds
                    )
                    update_locker_reservation(
                        db, locker_reservation.id, {"sale_end_time": new_sale_end_time}
                    )
                    # Sync locker_unit to Firebase after updating sale_end_time
                    sync_location_to_firebase_task.delay(
                        locker_reservation.locker_unit_id, is_unit_id=True
                    )

        # Update other fields (exclude products, sales_duration, and locker_unit_id as they're handled separately)
        for field, value in update.model_dump(
            exclude_unset=True,
            exclude={"products", "sales_duration", "locker_unit_id", "is_draft"},
        ).items():
            setattr(combo, field, value)

        # Update edited_at when combo is successfully edited
        combo.edited_at = get_current_time()

        # Save changes to database
        combo = update_combo(db, combo)

        logger.info(f"Successfully edited combo {combo_id}")

        # Return the same detailed response as get_combo_service
        return get_combo_service(combo_id, user, db)


def delete_combo_service(combo_id: str, user, db: Session, is_draft: bool = False):
    combo = get_combo_by_id(db, combo_id)
    if not combo:
        if is_draft:
            raise draft_already_deleted()
        else:
            raise combo_not_found()
    if is_draft and combo.is_draft == False:
        raise draft_already_sale_registered()

    if not can_manage_shop_products(user, combo.shop_id, db):
        raise shop_management_required()

    delete_combo(db, combo)
    return None


def get_product_master_service(product_master_id: str, user, db: Session):
    product_master = get_product_master(db, product_master_id)
    if not product_master:
        raise product_master_not_found()

    if user.role != "admin":
        user_shop = user.get_associated_shop()
        if user_shop and product_master.shop_id != user_shop.id:
            raise product_master_not_found()

    return ProductMasterRead.model_validate(product_master, from_attributes=True)


def list_product_masters_service(
    db: Session, user, name: str, limit: int = 20, offset: int = 0
):
    product_masters, total = get_product_masters(
        db, user=user, name=name, limit=limit, offset=offset
    )
    return [
        ProductMasterRead.model_validate(p, from_attributes=True)
        for p in product_masters
    ], total


def create_product_master_service(
    product_master: ProductMasterCreate, user, db: Session
):

    shop = get_shop(db, product_master.shop_id)
    if not shop:
        raise shop_not_found()

    if not can_manage_shop_products(user, product_master.shop_id, db):
        raise shop_management_required()

    # Check for duplicate product name in the same shop
    existing_product = get_product_master_by_name_and_shop(
        db, product_master.name, product_master.shop_id
    )
    if existing_product:
        raise product_already_exists()

    new_product_master = ProductMaster(**product_master.model_dump())
    new_product_master = create_product_master(db, new_product_master)
    return ProductMasterRead.model_validate(new_product_master, from_attributes=True)


def update_product_master_service(
    product_master_id: str, update: ProductMasterUpdate, user, db: Session
):
    product_master = get_product_master(db, product_master_id)
    if not product_master:
        raise product_master_not_found()
    if not product_master.is_active:
        raise product_master_already_deleted()
    if not can_manage_shop_products(user, product_master.shop_id, db):
        raise shop_management_required()

    # Check for duplicate product name if name is being updated
    update_data = update.model_dump(exclude_unset=True)
    if "name" in update_data:
        existing_product = get_product_master_by_name_and_shop(
            db,
            update_data["name"],
            product_master.shop_id,
            exclude_id=product_master_id,
        )
        if existing_product:
            raise product_already_exists()

    for field, value in update_data.items():
        setattr(product_master, field, value)
    product_master = update_product_master(db, product_master)
    return ProductMasterRead.model_validate(product_master, from_attributes=True)


def delete_product_master_service(product_master_id: str, user, db: Session):
    product_master = get_product_master(db, product_master_id)
    if not product_master:
        raise product_master_not_found()

    if not can_manage_shop_products(user, product_master.shop_id, db):
        raise shop_management_required()

    # Check if product master is used in any combo products
    combo_products = get_combo_products_by_product_master(db, product_master_id)
    if combo_products:
        delete_product_master(db, product_master)
        return {"message": "Deleted successfully"}
    else:
        # Not used: soft delete PM
        product_master.is_active = False
        product_master.updated_at = get_current_time()
        update_product_master(db, product_master)
        return {"message": "Deleted successfully"}


def publish_combo(combo_id: str, db: Session):
    """
    Publish a combo from draft to selling status
    """
    combo = get_combo_by_id(db, combo_id)
    if not combo:
        raise combo_not_found()

    if combo.status != "draft":
        raise Exception("Only draft combos can be published")

    combo.status = "selling"
    combo.is_draft = False
    combo = update_combo(db, combo)

    return ComboRead.model_validate(combo, from_attributes=True)


def set_combo_free_for_needy(combo_id: str, db: Session):
    """
    Manually set combo as free for people in need
    """
    combo = get_combo_by_id(db, combo_id)
    if not combo:
        raise combo_not_found()

    if combo.status not in ["selling", "discounted"]:
        raise Exception("Can only set selling or discounted combos as free")

    combo.status = "free"
    combo = update_combo(db, combo)

    return ComboRead.model_validate(combo, from_attributes=True)


def cancel_selling_combo_service(combo_id: str, user, db: Session):
    """
    Cancel a selling combo by changing its status to DELETED and updating related locker resources.

    Args:
        combo_id: The ID of the combo to cancel
        user: The user requesting cancellation
        db: Database session

    Returns:
        None: Returns None after successful cancellation

    Raises:
        combo_not_found: If combo doesn't exist
        combo_already_sold_cannot_cancel: If combo status is SOLD
        shop_management_required: If user doesn't have permission to manage the shop
    """
    from apps.core.logging import logger
    from apps.integrations.redis.lock import redis_lock

    # Use Redis distributed lock to prevent race condition with purchase
    logger.info(f"Attempting to acquire lock for combo cancellation: {combo_id}")
    with redis_lock(f"combo:{combo_id}", timeout=10, blocking_timeout=5):
        logger.info(f"Lock acquired for combo cancellation: {combo_id}")

        # Get combo with fresh data from DB
        combo = get_combo_by_id(db, combo_id)
        if not combo:
            raise combo_not_found()

        user_shop = user.get_associated_shop()
        if user.role == "owner_shop" and user_shop.id != combo.shop_id:
            raise combo_not_belong_to_shop()

        # Check if combo is already sold - cannot cancel
        if combo.status == COMBO_STATUS_SOLD:
            logger.warning(f"Combo {combo_id} already sold, cannot cancel")
            raise combo_already_sold_cannot_cancel()

        # Only cancel combos with SELLING status
        if combo.status != COMBO_STATUS_SELLING:
            logger.warning(
                f"Combo {combo_id} has invalid status for cancellation: {combo.status}"
            )
            raise combo_cannot_cancel_invalid_status(combo.status)

        # Update combo status to DELETED and set is_available to False
        combo.status = COMBO_STATUS_DELETED
        combo.is_available = False
        combo.updated_at = get_current_time()
        combo = update_combo(db, combo)
        logger.info(f"Combo {combo_id} status updated to DELETED")

        # Get locker reservation for this combo
        reservation = get_combo_locker_reservation(db, combo_id)

        if reservation:
            # Update locker_reservation status to COMPLETED
            update_locker_reservation(
                db, reservation.id, {"status": RESERVATION_STATUS_COMPLETED}
            )
            logger.info(f"Locker reservation {reservation.id} marked as COMPLETED")

            # Update locker_unit status to AVAILABLE
            if reservation.locker_unit_id:
                update_locker_unit(
                    db, reservation.locker_unit_id, {"status": UNIT_STATUS_AVAILABLE}
                )
                logger.info(
                    f"Locker unit {reservation.locker_unit_id} marked as AVAILABLE"
                )

        logger.info(f"Successfully cancelled combo {combo_id}")
        return None
