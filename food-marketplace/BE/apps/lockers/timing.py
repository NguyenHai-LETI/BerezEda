"""
Timing logic for locker reservations and combo management
"""

from datetime import datetime, timedelta
from typing import Optional

# Import combo statuses from core constants for consistency
from apps.core.constants import (
    COMBO_SALE_TIME_HOURS,
    COMBO_STATUS_EXPIRED,
    COMBO_STATUS_EXPIRED_PUT_IN_LOCKER,
    COMBO_STATUS_PREPARATION_TO_LOCKER,
    COMBO_STATUS_SELLING,
    SHOP_COOLDOWN_MINUTES,
)
from apps.core.utils import (
    format_time_remaining,
    get_current_time,
    is_time_expired,
    time_until,
)

# Legacy constants for backward compatibility - TODO: Remove these
COMBO_STATUS_LOCKER_RESERVED = COMBO_STATUS_PREPARATION_TO_LOCKER  # Legacy alias
COMBO_STATUS_FREE_FOR_NEEDY = "FREE_FOR_NEEDY"  # Not in current spec


def update_timing_after_placement(
    placement_time: datetime, sale_hours: int = COMBO_SALE_TIME_HOURS
) -> dict:
    """
    Recalculate timing after combo is actually placed in locker.

    Args:
        placement_time: When the combo was actually placed
        sale_hours: How many hours the combo will be available for sale

    Returns:
        dict with updated timing milestones
    """
    sale_end_time = placement_time + timedelta(hours=sale_hours)

    return {
        "sale_end_time": sale_end_time,
    }


def get_current_combo_status(
    reservation_created_at: datetime,
    preparation_deadline: datetime,
    item_deposited_at: Optional[datetime] = None,
    sale_end_time: Optional[datetime] = None,
    current_status: str = COMBO_STATUS_PREPARATION_TO_LOCKER,
) -> str:
    """
    Determine the current status of a combo based on timing.
    """
    now = get_current_time()

    if not item_deposited_at:
        if is_time_expired(preparation_deadline, now):
            return COMBO_STATUS_EXPIRED_PUT_IN_LOCKER
        else:
            return COMBO_STATUS_PREPARATION_TO_LOCKER

    if sale_end_time and is_time_expired(sale_end_time, now):
        return COMBO_STATUS_EXPIRED

    if item_deposited_at and current_status == COMBO_STATUS_PREPARATION_TO_LOCKER:
        return COMBO_STATUS_SELLING

    return current_status


def get_time_remaining_info(
    preparation_deadline: Optional[datetime] = None,
    sale_end_time: Optional[datetime] = None,
    item_deposited_at: Optional[datetime] = None,
) -> dict:
    """
    Get human-readable time remaining information.
    """
    now = get_current_time()
    info = {}

    if not item_deposited_at and preparation_deadline:
        time_left = preparation_deadline - now
        if time_left.total_seconds() > 0:
            info["preparation_time_left"] = format_time_remaining(time_left.total_seconds())
            info["preparation_expired"] = False
        else:
            info["preparation_time_left"] = "Expired"
            info["preparation_expired"] = True

    if item_deposited_at and sale_end_time:
        time_left = sale_end_time - now
        if time_left.total_seconds() > 0:
            info["sale_time_left"] = format_time_remaining(time_left.total_seconds())
            info["sale_expired"] = False
        else:
            info["sale_time_left"] = "Expired"
            info["sale_expired"] = True

    return info


def is_preparation_expired(preparation_deadline: datetime) -> bool:
    """Check if the preparation deadline has passed."""
    return is_time_expired(preparation_deadline)


def is_sale_period_expired(sale_end_time: datetime) -> bool:
    """Check if the sale period has ended."""
    return is_time_expired(sale_end_time)


def create_shop_cooldown(shop_id: str, failed_reservation_id: str) -> datetime:
    """
    Calculate cooldown end time for a shop after failed placement.

    Args:
        shop_id: Shop that failed to place combo
        failed_reservation_id: Reservation that timed out

    Returns:
        datetime: When the cooldown period ends
    """
    now = get_current_time()
    cooldown_end = now + timedelta(minutes=SHOP_COOLDOWN_MINUTES)
    return cooldown_end


def get_cooldown_remaining_time(cooldown_end: datetime) -> dict:
    """
    Get remaining cooldown time information.

    Args:
        cooldown_end: When the cooldown period ends

    Returns:
        dict: Cooldown status and remaining time info
    """
    now = get_current_time()
    if is_time_expired(cooldown_end, now):
        return {
            "in_cooldown": False,
            "remaining_time": "0 minutes",
            "can_reserve": True,
        }

    remaining_seconds = time_until(now, cooldown_end)
    remaining_time_str = format_time_remaining(remaining_seconds)

    return {
        "in_cooldown": True,
        "remaining_time": remaining_time_str,
        "cooldown_end": cooldown_end.isoformat(),
        "can_reserve": False,
    }
