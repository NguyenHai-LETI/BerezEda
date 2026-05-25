from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlmodel import Session

from apps.core.constants import (
    COMBO_STATUS_DELETED,
    COMBO_STATUS_EXPIRED,
    COMBO_STATUS_SOLD,
    MIN_FREE_PURCHASE_INTERVAL,
)
from apps.core.utils import get_current_time
from apps.orders.crud import get_latest_free_order
from apps.orders.exceptions import (
    app_version_too_old,
    combo_data_changed,
    combo_expired_time_sales,
    combo_not_available_for_purchase,
    free_combo_cooldown_not_met,
    invalid_order_status,
    wrong_data,
)
from apps.products.exceptions import combo_not_found
from apps.products.models import Combo


def validate_pickup_month(pickup_month: Optional[str]) -> None:
    if not pickup_month:
        return
    try:
        datetime.strptime(pickup_month + "-01", "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="pickup_month must be in YYYY-MM format",
        )


def validate_buy_combo(combo: Optional[Combo]) -> Combo:
    if not combo or combo.status == COMBO_STATUS_DELETED:
        raise combo_not_found()

    # Check if combo is available for purchase
    if not combo.is_available or combo.is_draft:
        raise combo_not_available_for_purchase()

    # Check if combo is already sold
    if combo.status == COMBO_STATUS_SOLD:
        raise invalid_order_status()

    if combo.status == COMBO_STATUS_EXPIRED:
        raise combo_expired_time_sales()
    return combo


def validate_cooldown_buy_free_combo(user, db: Session) -> None:
    """
    Validate cooldown for buying free combo.

    Logic:
    - Check the latest order with final_price = 0.0
    - If that order was completed more than 2 hours ago, return True (allow purchase)
    - Otherwise, raise exception (deny purchase)
    """
    latest_free_order = get_latest_free_order(db, user.id)
    # If no free order exists, allow purchase
    if not latest_free_order:
        return

    # Check if the latest free order was completed more than 2 hours ago
    current_time = get_current_time()
    free_purchase_interval = current_time - timedelta(
        minutes=MIN_FREE_PURCHASE_INTERVAL
    )

    # Use completed_at if available, otherwise use created_at
    order_time = latest_free_order.completed_at

    if order_time > free_purchase_interval:
        raise free_combo_cooldown_not_met()


def validate_combo_edited_at(combo: Combo, edited_at: Optional[datetime]) -> None:
    current = combo.edited_at
    # case 1: combo never edited
    if current is None:
        if edited_at is None:
            return
        raise wrong_data()

    # case 2: combo has been edited but app doest send edited_at
    if edited_at is None:
        raise app_version_too_old()

    # case 3: compare timestamp
    if edited_at < current:
        raise combo_data_changed()

    if edited_at > current:
        raise wrong_data()
