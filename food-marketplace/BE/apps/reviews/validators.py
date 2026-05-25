"""
Review Business Logic Validators

This module contains all business logic validation functions for reviews.
Keeps validation logic separate from constants and services.
"""

from sqlmodel import Session

from apps.reviews.schemas import ReviewCreate, ReviewUpdate


def validate_review_references(review: ReviewCreate, db: Session):
    """
    Validate that all referenced entities exist before creating a review.
    Raises appropriate exceptions if any referenced entity is not found.

    Args:
        review: Review data to validate
        db: Database session

    Raises:
        review_validation_error: If any referenced entity is not found
    """
    from apps.reviews.exceptions import review_validation_error

    # Validate shop exists if shop_id is provided
    if review.shop_id:
        from apps.shops.crud import get_shop

        shop = get_shop(db, review.shop_id)
        if not shop:
            raise review_validation_error(
                f"Shop with id {review.shop_id} does not exist"
            )

    # Validate combo exists if combo_id is provided
    if review.combo_id:
        from apps.products.crud import get_combo_by_id

        combo = get_combo_by_id(db, review.combo_id)
        if not combo:
            raise review_validation_error(
                f"Combo with id {review.combo_id} does not exist"
            )

    # Validate order exists if order_id is provided
    if review.order_id:
        from apps.orders.crud import get_order_by_id

        order = get_order_by_id(db, review.order_id)
        if not order:
            raise review_validation_error(
                f"Order with id {review.order_id} does not exist"
            )

    # Validate locker unit exists if locker_unit_id is provided
    if review.locker_unit_id:
        from apps.lockers.crud import get_locker_unit_by_id

        locker_unit = get_locker_unit_by_id(db, review.locker_unit_id)
        if not locker_unit:
            raise review_validation_error(
                f"Locker unit with id {review.locker_unit_id} does not exist"
            )


def validate_review_update_references(update: ReviewUpdate, db: Session):
    """
    Validate that all referenced entities exist before updating a review.
    Only validates fields that are being updated (exclude_unset=True).

    Args:
        update: Review update data to validate
        db: Database session

    Raises:
        review_validation_error: If any referenced entity is not found
    """
    from apps.reviews.exceptions import review_validation_error

    update_data = update.model_dump(exclude_unset=True)

    # Validate shop exists if shop_id is being updated
    if "shop_id" in update_data and update_data["shop_id"]:
        from apps.shops.crud import get_shop

        shop = get_shop(db, update_data["shop_id"])
        if not shop:
            raise review_validation_error(
                f"Shop with id {update_data['shop_id']} does not exist"
            )

    # Validate combo exists if combo_id is being updated
    if "combo_id" in update_data and update_data["combo_id"]:
        from apps.products.crud import get_combo_by_id

        combo = get_combo_by_id(db, update_data["combo_id"])
        if not combo:
            raise review_validation_error(
                f"Combo with id {update_data['combo_id']} does not exist"
            )

    # Validate order exists if order_id is being updated
    if "order_id" in update_data and update_data["order_id"]:
        from apps.orders.crud import get_order_by_id

        order = get_order_by_id(db, update_data["order_id"])
        if not order:
            raise review_validation_error(
                f"Order with id {update_data['order_id']} does not exist"
            )

    # Validate locker unit exists if locker_unit_id is being updated
    if "locker_unit_id" in update_data and update_data["locker_unit_id"]:
        from apps.lockers.crud import get_locker_unit_by_id

        locker_unit = get_locker_unit_by_id(db, update_data["locker_unit_id"])
        if not locker_unit:
            raise review_validation_error(
                f"Locker unit with id {update_data['locker_unit_id']} does not exist"
            )


def validate_rating_range(rating: int) -> bool:
    """
    Validate that rating is within acceptable range (1-5).

    Args:
        rating: Rating value to validate

    Returns:
        bool: True if rating is valid, False otherwise
    """
    return 1 <= rating <= 5


def validate_comment_length(comment: str, max_length: int = 1000) -> bool:
    """
    Validate that comment is not too long.

    Args:
        comment: Comment text to validate
        max_length: Maximum allowed length (default: 1000)

    Returns:
        bool: True if comment length is valid, False otherwise
    """
    if not comment:
        return True  # Empty comments are allowed
    return len(comment.strip()) <= max_length
