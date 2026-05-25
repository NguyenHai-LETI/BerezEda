"""
Notification Utility Functions

Common utility functions for notification services and resource cleanup.
"""

import logging
from typing import Set

from sqlmodel import Session, select

from apps.core.constants import RESERVATION_STATUS_COMPLETED, UNIT_STATUS_AVAILABLE
from apps.lockers.models.reservation import LockerReservation
from apps.lockers.models.unit import LockerUnit
from apps.lockers.tasks import sync_location_to_firebase_task


def complete_reservation_and_release_locker(
    session: Session, combo_id: str
) -> tuple[int, Set[str]]:
    """
    Complete reservations for a combo and release associated locker units.

    This is a common operation when combos expire or orders are cancelled.

    Args:
        session: Database session
        combo_id: ID of the combo to cleanup

    Returns:
        Tuple of (updated_units_count, set_of_location_ids_synced)
    """
    try:
        # Get all reservations for this combo
        reservations = session.exec(
            select(LockerReservation).where(LockerReservation.combo_id == combo_id)
        ).all()

        if not reservations:
            return 0, set()

        updated_units = 0
        synced_locations: Set[str] = set()

        for reservation in reservations:
            try:
                reservation.status = RESERVATION_STATUS_COMPLETED
                session.add(reservation)

                # Release the locker unit if exists
                if reservation.locker_unit_id:
                    locker_unit = session.get(LockerUnit, reservation.locker_unit_id)

                    if locker_unit and locker_unit.status != UNIT_STATUS_AVAILABLE:
                        locker_unit.status = UNIT_STATUS_AVAILABLE
                        session.add(locker_unit)
                        updated_units += 1

                        if locker_unit.location_id:
                            synced_locations.add(str(locker_unit.location_id))

            except Exception as e:
                logging.error(
                    f"Failed to process reservation {reservation.id}: {str(e)}"
                )

        session.commit()

        if synced_locations:
            import time

            time.sleep(0.1)

            for location_id in synced_locations:
                sync_location_to_firebase_task.apply_async(
                    args=[location_id], countdown=2
                )

        return updated_units, synced_locations

    except Exception as e:
        session.rollback()
        logging.error(f"Failed to complete reservations for combo {combo_id}: {str(e)}")
        raise
