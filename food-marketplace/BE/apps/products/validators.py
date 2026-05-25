"""
Product Business Logic Validators

This module contains all business logic validation functions for products/combos.
Keeps validation logic separate from constants and services.
"""

from sqlmodel import Session

from apps.core.constants import (  # Used instead of CANCELLED per spec; Used instead of LOCKER_RESERVED per spec; This should be ORDER status, not COMBO status
    COMBO_DELETABLE_STATUSES,
    COMBO_STATUS_DELETED,
    COMBO_STATUS_EXPIRED,
    COMBO_STATUS_PREPARATION_TO_LOCKER,
    COMBO_STATUS_SELLING,
    COMBO_STATUS_SOLD,
    COMBO_UPDATABLE_STATUSES,
    ORDER_STATUS_PICKED_UP,
    UNIT_STATUS_AVAILABLE,
)
from apps.products.exceptions import draft_already_sale_registered

# Legacy constants for backward compatibility - TODO: Remove these
COMBO_STATUS_FREE_FOR_NEEDY = "FREE_FOR_NEEDY"  # Not in current spec

# TODO: These should be defined in core constants if needed
COMBO_NON_UPDATABLE_STATUSES = []  # Define this properly
COMBO_STATUS_TRANSITIONS = {}  # Define this properly


def get_active_statuses() -> list:
    """Get statuses where combo is still available for purchase"""
    return [
        COMBO_STATUS_SELLING,
        COMBO_STATUS_FREE_FOR_NEEDY,
    ]


def get_completed_statuses() -> list:
    """Get statuses where combo lifecycle is complete"""
    return [ORDER_STATUS_PICKED_UP, COMBO_STATUS_EXPIRED, COMBO_STATUS_DELETED]


def can_transition_status(current_status: str, new_status: str) -> bool:
    """
    Check if status transition is allowed based on COMBO_STATUS_TRANSITIONS rules

    Args:
        current_status: Current combo status
        new_status: Desired new status

    Returns:
        bool: True if transition is allowed, False otherwise
    """
    if current_status == new_status:
        return True

    allowed_transitions = COMBO_STATUS_TRANSITIONS.get(current_status, [])
    return new_status in allowed_transitions


def get_in_progress_statuses() -> list:
    """Get statuses where combo/locker setup is in progress"""
    return [
        COMBO_STATUS_PREPARATION_TO_LOCKER,
        COMBO_STATUS_SELLING,
        COMBO_STATUS_SOLD,  # Purchased but not picked up yet
    ]


def is_combo_available_for_purchase(status: str) -> bool:
    """Check if combo can be purchased in current status"""
    return status in get_active_statuses()


def is_locker_setup_in_progress(status: str) -> bool:
    """Check if locker is reserved but combo not yet placed (15min window)"""
    return status == COMBO_STATUS_PREPARATION_TO_LOCKER


def is_combo_ready_to_publish(status: str) -> bool:
    """Check if combo is in locker and ready to be published for sale"""
    return status == COMBO_STATUS_SELLING


def can_delete_combo(status: str) -> bool:
    """Check if combo can be deleted in current status"""
    return status in COMBO_DELETABLE_STATUSES


def can_update_combo(status: str) -> bool:
    """Check if combo can be updated in current status"""
    return status in COMBO_UPDATABLE_STATUSES


def can_fully_update_combo(status: str) -> bool:
    """Check if combo can be fully updated (all fields) in current status"""
    return status in COMBO_UPDATABLE_STATUSES


def validate_combo_for_deletion(combo) -> tuple[bool, str]:
    """
    Validate if combo can be deleted and return validation result with message

    Returns:
        tuple: (is_valid, error_message)
    """
    if not can_delete_combo(combo.status):
        return (
            False,
            f"Cannot delete combo in status '{combo.status}'. Only combos in {COMBO_DELETABLE_STATUSES} can be deleted.",
        )

    return True, ""


from typing import Optional


def validate_combo_for_update(
    combo, update_fields: Optional[list] = None, update_data: Optional[dict] = None
) -> tuple[bool, str]:
    """
    Validate if combo can be updated and return validation result with message

    Args:
        combo: The combo object to validate
        update_fields: List of fields being updated (optional)
        update_data: Dictionary of update field values (optional)

    Returns:
        tuple: (is_valid, error_message)
    """
    if not can_update_combo(combo.status):
        return (
            False,
            f"Cannot update combo in status '{combo.status}'. Updates not allowed for this status.",
        )

    if combo.status == COMBO_STATUS_SELLING:
        # Check if trying to set is_draft from False to True
        if update_data and "is_draft" in update_data:
            new_is_draft = update_data.get("is_draft")
            if combo.is_draft == False and new_is_draft == True:
                raise draft_already_sale_registered()

        if update_fields:
            # Only allow certain fields to be updated when sold
            # Products cannot be updated once sold to anyone
            allowed_fields_when_sold = ["internal_notes", "admin_comments"]
            restricted_fields = [
                field
                for field in update_fields
                if field not in allowed_fields_when_sold
            ]
            if restricted_fields:
                # Special message for products field
                if "products" in restricted_fields:
                    return (
                        False,
                        "Cannot update products of a combo that has been sold to customers.",
                    )
                return (
                    False,
                    f"Cannot update fields {restricted_fields} when combo is sold.",
                )

    return True, ""


def validate_status_transition(
    current_status: str, new_status: str
) -> tuple[bool, str]:
    """
    Validate if status transition is allowed and return validation result with message

    Returns:
        tuple: (is_valid, error_message)
    """
    if not can_transition_status(current_status, new_status):
        allowed_transitions = COMBO_STATUS_TRANSITIONS.get(current_status, [])
        return (
            False,
            f"Cannot transition from '{current_status}' to '{new_status}'. Allowed transitions: {allowed_transitions}",
        )

    return True, ""


def validate_combo_for_purchase(combo) -> tuple[bool, str]:
    """
    Validate if combo can be purchased

    Returns:
        tuple: (is_valid, error_message)
    """
    if not is_combo_available_for_purchase(combo.status):
        return (
            False,
            f"Combo is not available for purchase. Current status: {combo.status}",
        )

    if not combo.is_available:
        return False, "Combo is marked as not available"

    # Add more purchase validation logic here (stock, timing, etc.)

    return True, ""


def validate_locker_reservation(locker_unit_id: str, shop_id: str, db):
    """
    Validate that an active locker reservation exists for the given unit and shop.

    Args:
        locker_unit_id: The locker unit ID to validate
        shop_id: The shop ID that should own the reservation
        db: Database session

    Returns:
        LockerReservation: The found reservation

    Raises:
        HTTPException: If no active reservation is found
    """
    from fastapi import HTTPException

    from apps.lockers.crud import get_locker_reservation_by_unit_and_shop

    locker_reservation = get_locker_reservation_by_unit_and_shop(
        db, locker_unit_id, shop_id
    )

    if not locker_reservation:
        raise HTTPException(
            status_code=400,
            detail="No active reservation found for this locker unit and shop",
        )

    return locker_reservation


def validate_locker_unit_availability_for_relisting(
    db: Session, combo_id: str, logger
) -> None:
    """
    Validate that the locker unit associated with an expired combo is available for re-listing.
    """
    from apps.lockers.crud import (
        get_locker_reservations_by_combo_id,
        get_locker_unit_by_id,
    )
    from apps.lockers.exceptions import locker_unit_not_available

    locker_reservation = get_locker_reservations_by_combo_id(db, combo_id)
    if locker_reservation and locker_reservation.locker_unit_id:
        locker_unit = get_locker_unit_by_id(db, locker_reservation.locker_unit_id)
        if locker_unit and locker_unit.status != UNIT_STATUS_AVAILABLE:
            logger.warning(
                f"Cannot re-list expired combo {combo_id}: "
                f"locker unit {locker_unit.id} status is {locker_unit.status}, not AVAILABLE"
            )
            raise locker_unit_not_available()
