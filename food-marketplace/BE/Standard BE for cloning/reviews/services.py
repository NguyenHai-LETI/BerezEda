from typing import Optional

from sqlmodel import Session

from apps.core.schemas import DEFAULT_LIMIT, DEFAULT_OFFSET
from apps.integrations.celery.shops.tasks import send_user_review
from apps.orders.crud import get_order_by_combo
from apps.products.crud import get_combo_locker_reservation
from apps.reviews import crud
from apps.reviews.exceptions import review_comment_required, review_not_found
from apps.reviews.models.reviews import Review
from apps.reviews.validators import (
    validate_review_references,
    validate_review_update_references,
)
from apps.users.models import User

from .schemas import ReviewCreate, ReviewDetailRead, ReviewRead, ReviewUpdate


def list_reviews_service(
    db: Session, user: User, limit: Optional[int] = None, offset: Optional[int] = None
):
    """List reviews with detailed nested data.
    If limit and offset are None, returns all reviews."""
    reviews, total = crud.get_reviews_with_relationships(db, user, limit, offset)
    return [ReviewDetailRead.model_validate(r) for r in reviews], total


def list_reviews_basic_service(
    db: Session, limit: int = DEFAULT_LIMIT, offset: int = DEFAULT_OFFSET
):
    """List reviews with basic data (for backwards compatibility)"""
    reviews, total = crud.get_reviews(db, limit, offset)
    return [ReviewRead.model_validate(r) for r in reviews], total


def create_review_service(review: ReviewCreate, user_id: str, db: Session):

    if not review.comment or not review.comment.strip():
        raise review_comment_required()

    validate_review_references(review, db)

    # Create review data with user_id from authenticated user
    review_data = review.model_dump()
    review_data["user_id"] = user_id

    # Auto-link order and locker info if not explicitly provided
    order = get_order_by_combo(db, review_data["combo_id"])  # latest/first for combo
    if order and getattr(order, "user_id", None) == user_id:
        review_data["order_id"] = order.id
        if getattr(order, "locker_unit_id", None) and not review_data.get(
            "locker_unit_id"
        ):
            review_data["locker_unit_id"] = order.locker_unit_id

    reservation = get_combo_locker_reservation(db, review_data["combo_id"])
    if reservation and getattr(reservation, "locker_unit_id", None):
        review_data["locker_unit_id"] = reservation.locker_unit_id

    new_review = Review(**review_data)
    new_review = crud.create_review(db, new_review)

    # Send notification to shop owner about new review
    if new_review.combo_id and new_review.shop_id:
        from apps.shops.crud import get_shop_with_users

        shop = get_shop_with_users(db, new_review.shop_id)
        if shop:
            users_to_notify = shop.get_all_shop_users()

            if users_to_notify:
                # Extract user IDs from User objects
                user_ids = [user.id for user in users_to_notify]
                # Use new_review_id parameter (updated in celery task)
                send_user_review.delay(
                    combo_id=str(new_review.combo_id),
                    user_ids=user_ids,
                    new_review_id=str(new_review.id),
                )

    # Get review with relationships for response
    review_with_relationships = crud.get_review_with_relationships(db, new_review.id)
    return ReviewDetailRead.model_validate(review_with_relationships)


def get_review_service(review_id: str, db: Session):
    """Get review with detailed nested data"""
    review = crud.get_review_with_relationships(db, review_id)
    if not review:
        raise review_not_found()
    return ReviewDetailRead.model_validate(review)


def get_review_basic_service(review_id: str, db: Session):
    """Get review with basic data (for backwards compatibility)"""
    review = crud.get_review(db, review_id)
    if not review:
        raise review_not_found()
    return ReviewRead.model_validate(review)


def update_review_service(review_id: str, db: Session, update: ReviewUpdate):
    review = crud.get_review(db, review_id)
    if not review:
        raise review_not_found()

    # Validate that any new references exist before updating
    validate_review_update_references(update, db)

    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(review, field, value)
    review = crud.update_review(db, review)

    # Get review with relationships for response
    review_with_relationships = crud.get_review_with_relationships(db, review.id)
    return ReviewDetailRead.model_validate(review_with_relationships)


def delete_review_service(review_id: str, db: Session):
    review = crud.get_review(db, review_id)
    if not review:
        raise review_not_found()
    crud.delete_review(db, review)
    return None
