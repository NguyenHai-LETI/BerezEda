"""
Sales Management Utility Functions

Helper functions for countdown calculations, time formatting, and status logic.
"""

from datetime import datetime
from typing import Optional, Tuple

from apps.core.constants import (
    COMBO_STATUS_DELETED,
    COMBO_STATUS_EXPIRED,
    COMBO_STATUS_EXPIRED_PUT_IN_LOCKER,
    COMBO_STATUS_PREPARATION_TO_LOCKER,
    COMBO_STATUS_SELLING,
    COMBO_STATUS_SOLD,
    ORDER_STATUS_PICKED_UP,
    ORDER_STATUS_READY_FOR_PICKUP,
)
from apps.core.utils import get_current_time
from apps.products.models.combos import Combo
from apps.sales_management.constants import (
    DATETIME_DISPLAY_FORMAT,
    STATUS_DISPLAY_MAPPING,
)


def format_datetime_for_display(dt: Optional[datetime]) -> Optional[str]:
    """
    Format datetime for Japanese UI display.

    Args:
        dt: Datetime to format

    Returns:
        Formatted string in YYYY/MM/DD/HH:MM format or None
    """
    if not dt:
        return None
    return dt.strftime(DATETIME_DISPLAY_FORMAT)


def get_countdown_seconds(
    preparation_deadline: Optional[datetime],
) -> Tuple[Optional[int], Optional[str]]:
    countdown_seconds = None
    countdown_display = None
    if preparation_deadline:
        countdown_display = format_datetime_for_display(preparation_deadline)
        # Calculate remaining seconds until deadline
        current_time = get_current_time()
        time_diff = preparation_deadline - current_time
        countdown_seconds = max(0, int(time_diff.total_seconds()))
    return countdown_seconds, countdown_display


def get_info_display_info(combo: Combo, reservation=None) -> dict:
    """
    Get display information for a combo status.

    Args:
        combo: Combo object containing status, orders, and reservation info
        reservation: Optional LockerReservation object for preparation deadline calculations

    Returns:
        Dict containing display information with keys:
        - display_time: Formatted time string
        - display_time_label: Label for the time
        - display_status_text: Status text for UI
        - countdown_seconds: Remaining seconds (for countdowns)
        - countdown_display: Formatted countdown display
    """
    display_time = None
    display_time_label = None
    display_status_text = ""
    countdown_seconds = None
    countdown_display = None

    # Safely get the first order if combo is sold
    order = None
    if combo.status == COMBO_STATUS_SOLD and combo.orders:
        order = combo.orders[0]

    if order:
        if order.status == ORDER_STATUS_PICKED_UP:
            display_time = format_datetime_for_display(order.picked_up_at)
        else:
            display_time = format_datetime_for_display(order.completed_at)

        display_time_label = "Completed Time"

        if order.status == ORDER_STATUS_PICKED_UP:
            display_status_text = STATUS_DISPLAY_MAPPING.get("picked_up", "Picked Up")

        elif order.status == ORDER_STATUS_READY_FOR_PICKUP:
            if order.final_price == 0:
                display_status_text = STATUS_DISPLAY_MAPPING.get(
                    "donation_ready_for_pickup", "Ready for Donation Pickup"
                )
            else:
                display_status_text = STATUS_DISPLAY_MAPPING.get(
                    "ready_for_pickup", "Ready for Pickup"
                )
        elif order.status == "EXPIRED":  # legacy status: no longer set but may exist in old orders
            display_status_text = STATUS_DISPLAY_MAPPING.get(
                "selling_expired", "Order Expired"
            )
    else:
        display_time = format_datetime_for_display(combo.listing_end_date)
        display_time_label = "Sale End Time"

        if combo.status == COMBO_STATUS_DELETED:
            display_status_text = STATUS_DISPLAY_MAPPING.get("deleted", "Deleted")
        if combo.status == COMBO_STATUS_SELLING:
            if combo.is_free:
                display_status_text = STATUS_DISPLAY_MAPPING.get(
                    "free", "Free/Donation"
                )
            else:
                display_status_text = STATUS_DISPLAY_MAPPING.get("selling", "On Sale")

        elif combo.status == COMBO_STATUS_EXPIRED:
            display_status_text = STATUS_DISPLAY_MAPPING.get(
                "selling_expired", "Sale Expired"
            )

        elif combo.status == COMBO_STATUS_PREPARATION_TO_LOCKER:
            # Calculate countdown if reservation with preparation_deadline is provided
            if reservation and reservation.preparation_deadline:
                countdown_seconds, countdown_display = get_countdown_seconds(
                    reservation.preparation_deadline
                )
                display_time = countdown_display
                display_time_label = "Placement Deadline"
            else:
                display_time_label = "Placement Deadline"
            display_status_text = STATUS_DISPLAY_MAPPING.get(
                "preparation_to_locker", "Preparing for Locker"
            )

        elif combo.status == COMBO_STATUS_EXPIRED_PUT_IN_LOCKER:
            display_status_text = STATUS_DISPLAY_MAPPING.get(
                "preparation_to_locker", "Placement Deadline Expired"
            )

    return {
        "display_time": display_time,
        "display_time_label": display_time_label,
        "display_status_text": display_status_text,
        "countdown_seconds": countdown_seconds,
        "countdown_display": countdown_display,
    }


def has_picked_up_orders(combo):
    """
    Check if a combo has any picked up orders.

    Args:
        combo: Combo object to check

    Returns:
        True if there are picked up orders, False otherwise
    """
    return any(order.status == ORDER_STATUS_PICKED_UP for order in combo.orders)
