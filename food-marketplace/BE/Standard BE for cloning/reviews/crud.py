from typing import Optional

from sqlalchemy import desc
from sqlmodel import Session, func, select

from apps.reviews.models.reviews import Review
from apps.shops.crud import get_shop_by_code
from apps.users.models import User


def get_review(db: Session, review_id: str):
    return db.get(Review, review_id)


def get_review_with_relationships(db: Session, review_id: str):
    """Get review with loaded relationships for detailed response"""
    # Get the review first
    review = db.get(Review, review_id)
    if not review:
        return None

    related_ids = {
        "user_id": review.user_id,
        "shop_id": review.shop_id,
        "combo_id": review.combo_id,
        "order_id": review.order_id,
        "locker_unit_id": review.locker_unit_id,
    }

    # Load related entities in batch queries
    user = None
    if related_ids["user_id"]:
        from apps.users.models.users import User

        user = db.get(User, related_ids["user_id"])

    shop = None
    if related_ids["shop_id"]:
        from apps.shops.models.shops import Shop

        shop = db.get(Shop, related_ids["shop_id"])

    combo = None
    if related_ids["combo_id"]:
        from apps.products.models.combos import Combo

        combo = db.get(Combo, related_ids["combo_id"])

    order = None
    if related_ids["order_id"]:
        from apps.orders.models.orders import Order

        order = db.get(Order, related_ids["order_id"])

    locker_location = None
    locker_unit = None
    if related_ids["locker_unit_id"]:
        from apps.lockers.models.location import LockerLocation
        from apps.lockers.models.unit import LockerUnit

        locker_unit = db.get(LockerUnit, related_ids["locker_unit_id"])
        if locker_unit and locker_unit.location_id:
            locker_location = db.get(LockerLocation, locker_unit.location_id)

    # Build response dict using the loaded entities
    review_data = {
        "id": review.id,
        "rating": review.rating,
        "comment": review.comment,
        "created_at": review.created_at,
        "updated_at": review.updated_at,
        "user": {"id": user.id, "icon": user.icon} if user else None,
        "shop": (
            {
                "id": shop.id,
                "name": shop.name,
                "code": shop.code,
                "phone": shop.phone,
                "address": shop.address,
            }
            if shop
            else None
        ),
        "combo": (
            {
                "id": combo.id,
                "name": combo.name,
                "description": combo.description,
                "images": combo.images,
                "product_number": combo.product_number,
                "category": combo.category,
                "original_price": combo.original_price,
                "discount_percentage": combo.discount_percentage,
                "status": combo.status,
            }
            if combo
            else None
        ),
        "order": (
            {
                "id": order.id,
                "order_number": order.order_number,
                "status": order.status,
                "original_price": order.original_price,
                "discount_percentage": order.discount_percentage,
                "final_price": order.final_price,
                "pickup_deadline": order.pickup_deadline,
                "picked_up_at": order.picked_up_at or order.pickup_deadline,
                "created_at": order.created_at,
            }
            if order
            else None
        ),
        "locker": (
            {
                "id": locker_location.id,
                "name": locker_location.name,
                "code": locker_location.code,
                "address": locker_location.address,
                "position": locker_location.position,
            }
            if locker_location
            else None
        ),
        "locker_unit": (
            {
                "id": locker_unit.id,
                "location_id": locker_unit.location_id,
                "unit_number": locker_unit.unit_number,
                "full_unit_number": locker_unit.full_unit_number,
                "size": locker_unit.size,
                "status": locker_unit.status,
                "temperature": locker_unit.temperature,
                "column_index": locker_unit.column_index,
                "is_active": locker_unit.is_active,
                "created_at": locker_unit.created_at,
                "updated_at": locker_unit.updated_at,
            }
            if locker_unit
            else None
        ),
    }

    return review_data


def get_reviews(db: Session, limit: int = 10, offset: int = 0):
    # Count total reviews
    count_statement = select(func.count()).select_from(Review)
    total = db.exec(count_statement).one()

    # Get paginated reviews
    statement = (
        select(Review).order_by(desc(Review.created_at)).offset(offset).limit(limit)
    )
    reviews = db.exec(statement).all()
    return reviews, total


def count_reviews_by_shop_id(db: Session, shop_id: int):
    count_stmt = (
        select(func.count()).select_from(Review).where(Review.shop_id == shop_id)
    )
    total = db.exec(count_stmt).first()
    return total


def get_reviews_with_relationships(
    db: Session, user: User, limit: Optional[int] = None, offset: Optional[int] = None
):
    """Get reviews with loaded relationships for detailed response.
    If limit and offset are None, returns all reviews."""

    # Build base query with WHERE conditions (BEFORE limit/offset)
    base_statement = select(Review)

    if user.role == "customer":
        base_statement = base_statement.where(Review.user_id == user.id)
    elif user.role == "owner_shop":
        shop = get_shop_by_code(db, user.code_shop)
        if not shop:
            # If shop not found, return empty results
            return [], 0
        base_statement = base_statement.where(Review.shop_id == shop.id)

    # Calculate total count using base statement (without order_by, limit, offset)
    count_statement = select(func.count()).select_from(base_statement.subquery())
    total = db.exec(count_statement).one()

    # Apply order_by, limit/offset AFTER WHERE conditions for the actual query
    statement = base_statement.order_by(desc(Review.created_at))
    if offset is not None:
        statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)
    reviews = db.exec(statement).all()

    if not reviews:
        return [], total

    # Since we have relationships defined, we can simplify this
    # Just access the relationships directly - SQLModel will handle lazy loading
    reviews_data = []
    for review in reviews:
        # Access relationships directly - they're already defined in the model
        review_data = {
            "id": review.id,
            "rating": review.rating,
            "comment": review.comment,
            "created_at": review.created_at,
            "updated_at": review.updated_at,
            "user": (
                {"id": review.user.id, "icon": review.user.icon}
                if review.user
                else None
            ),
            "shop": (
                {
                    "id": review.shop.id,
                    "name": review.shop.name,
                    "code": review.shop.code,
                    "phone": review.shop.phone,
                    "address": review.shop.address,
                }
                if review.shop
                else None
            ),
            "combo": (
                {
                    "id": review.combo.id,
                    "name": review.combo.name,
                    "description": review.combo.description,
                    "images": review.combo.images,
                    "product_number": review.combo.product_number,
                    "category": review.combo.category,
                    "original_price": review.combo.original_price,
                    "discount_percentage": review.combo.discount_percentage,
                    "status": review.combo.status,
                }
                if review.combo
                else None
            ),
            "order": (
                {
                    "id": review.order.id,
                    "order_number": review.order.order_number,
                    "status": review.order.status,
                    "original_price": review.order.original_price,
                    "discount_percentage": review.order.discount_percentage,
                    "final_price": review.order.final_price,
                    "pickup_deadline": review.order.pickup_deadline,
                    "picked_up_at": review.order.picked_up_at
                    or review.order.pickup_deadline,
                    "created_at": review.order.created_at,
                }
                if review.order
                else None
            ),
            "locker": (
                {
                    "id": review.locker_unit.location.id,
                    "name": review.locker_unit.location.name,
                    "code": review.locker_unit.location.code,
                    "address": review.locker_unit.location.address,
                    "position": review.locker_unit.location.position,
                }
                if review.locker_unit and review.locker_unit.location
                else None
            ),
            "locker_unit": (
                {
                    "id": review.locker_unit.id,
                    "location_id": review.locker_unit.location_id,
                    "unit_number": review.locker_unit.unit_number,
                    "full_unit_number": review.locker_unit.full_unit_number,
                    "size": review.locker_unit.size,
                    "status": review.locker_unit.status,
                    "temperature": review.locker_unit.temperature,
                    "column_index": review.locker_unit.column_index,
                    "is_active": review.locker_unit.is_active,
                    "created_at": review.locker_unit.created_at,
                    "updated_at": review.locker_unit.updated_at,
                }
                if review.locker_unit
                else None
            ),
        }

        reviews_data.append(review_data)

    return reviews_data, total


def create_review(db: Session, review: Review):
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def update_review(db: Session, review: Review):
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def delete_review(db: Session, review: Review):
    db.delete(review)
    db.commit()
