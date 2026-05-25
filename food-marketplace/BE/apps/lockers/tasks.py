# Import all models to ensure SQLAlchemy relationships are properly resolved
import os
from datetime import datetime, timedelta

from sqlmodel import Session, select

from apps.core.celery_app import celery_app
from apps.core.constants import (
    COMBO_STATUS_EXPIRED_PUT_IN_LOCKER,
    RESERVATION_STATUS_ACTIVE,
    RESERVATION_STATUS_PENDING,
    UNIT_STATUS_OCCUPIED,
)
from apps.core.logging import logger
from apps.core.utils import get_current_time
from apps.integrations.firebase.locker_service import firebase_locker_service
from apps.lockers.crud import get_locker_unit_by_id


@celery_app.task(name="sync_location_to_firebase")
def sync_location_to_firebase_task(target_id: str, is_unit_id: bool = False) -> dict:
    """
    Async task to sync locker location with its units to Firebase.

    Args:
        target_id: ID of the location to sync or unit ID if is_unit_id=True
        is_unit_id: If True, target_id is a unit_id and we need to find its location

    Returns:
        dict: Result of the sync operation
    """

    location_id = None
    try:
        from apps.core.database import get_session
        from apps.lockers import crud
        from apps.lockers.models.reservation import LockerReservation
        from apps.lockers.models.shop_locker_association import ShopLockerAssociation
        from apps.shops.models.shops import Shop

        # Get location and its units from database
        db_gen = get_session()
        db: Session = next(db_gen)
        try:
            if is_unit_id:
                # Single unit update - optimized path
                unit = crud.get_locker_unit_by_id(db, target_id)
                if not unit:
                    return {
                        "status": "error",
                        "unit_id": target_id,
                        "error": "Unit not found",
                    }
                location_id = unit.location_id

                # For single unit updates, only load the specific unit with its reservations
                unit_reservations = db.exec(
                    select(LockerReservation).where(
                        LockerReservation.locker_unit_id == target_id
                    )
                ).all()
                unit.reservations = list(unit_reservations)

                # Sync just this unit using the single unit method
                try:
                    result = firebase_locker_service.sync_single_unit_to_firebase(
                        location_id, unit
                    )
                    if result:
                        logger.info(
                            f"Successfully updated unit {target_id} in Firebase"
                        )
                        return {
                            "status": "success",
                            "unit_id": target_id,
                            "location_id": location_id,
                            "action": "single_unit_sync",
                        }
                    else:
                        logger.error(f"Failed to update unit {target_id} in Firebase")
                        return {
                            "status": "error",
                            "unit_id": target_id,
                            "error": "Unit sync failed",
                        }
                except Exception as e:
                    logger.error(
                        f"Firebase unit sync failed for unit {target_id}: {str(e)}"
                    )
                    return {"status": "error", "unit_id": target_id, "error": str(e)}

            else:
                # Full location sync - comprehensive path
                location_id = target_id

                location = crud.get_locker_location_by_id(db, location_id)
                if not location:
                    return {
                        "status": "error",
                        "location_id": location_id,
                        "error": "Location not found",
                    }

                # Efficiently load associated shops using JOIN
                shops_query = (
                    select(Shop)
                    .join(ShopLockerAssociation)
                    .where(ShopLockerAssociation.locker_location_id == location_id)
                )
                shops = list(db.exec(shops_query).all())

                # Get units for this location (consider pagination for large datasets)
                units, total_units = crud.get_locker_units(
                    db, location_id=location_id, limit=1000
                )

                if total_units > 1000:
                    logger.warning(
                        f"Location {location_id} has {total_units} units, "
                        "only processing first 1000. Consider implementing pagination."
                    )

                # Efficiently load all reservations for these units in one query
                if units:
                    unit_ids = [unit.id for unit in units]
                    reservations_query = select(LockerReservation).where(
                        LockerReservation.locker_unit_id.in_(unit_ids)
                    )
                    all_reservations = db.exec(reservations_query).all()

                    # Group reservations by unit_id for efficient lookup
                    reservations_by_unit = {}
                    for reservation in all_reservations:
                        unit_id = reservation.locker_unit_id
                        if unit_id not in reservations_by_unit:
                            reservations_by_unit[unit_id] = []
                        reservations_by_unit[unit_id].append(reservation)

                    # Assign reservations to units
                    for unit in units:
                        unit.reservations = reservations_by_unit.get(unit.id, [])

                # Prepare data for Firebase sync (ensure shops are available to location)
                # The Firebase service looks for _shops_for_sync attribute on location
                location._shops_for_sync = shops

                # Call the Firebase sync function (full location sync)
                try:
                    result = firebase_locker_service.sync_location_to_firebase(
                        location, units
                    )
                except Exception as e:
                    logger.error(
                        f"Firebase full sync failed for location {location_id}: {str(e)}"
                    )
                    result = False

                if result:
                    logger.info(
                        f"Successfully synced location {location_id} ({len(units)} units, "
                        f"{len(shops)} shops) to Firebase via task"
                    )
                    return {
                        "status": "success",
                        "location_id": location_id,
                        "units_synced": len(units),
                        "shops_synced": len(shops),
                        "action": "full_location_sync",
                    }
                else:
                    logger.error(
                        f"Failed to sync location {location_id} to Firebase via task"
                    )
                    return {
                        "status": "error",
                        "location_id": location_id,
                        "error": "Full location sync operation returned False",
                    }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error in sync_location_to_firebase_task: {str(e)}")
        return {
            "status": "error",
            "target_id": target_id,
            "location_id": location_id,
            "error": str(e),
        }


@celery_app.task(name="delete_location_from_firebase")
def delete_location_from_firebase_task(location_id: str) -> dict:
    """
    Async task to delete location from Firebase.

    Args:
        location_id: Location ID to delete

    Returns:
        dict: Result of the delete operation
    """
    try:
        import asyncio

        async def run_delete():
            return await firebase_locker_service.delete_location_from_firebase(
                location_id
            )

        # Run the async function
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        success = loop.run_until_complete(run_delete())

        if success:
            logger.info(
                f"Successfully deleted location {location_id} from Firebase via task"
            )
            return {"status": "success", "location_id": location_id}
        else:
            logger.error(
                f"Failed to delete location {location_id} from Firebase via task"
            )
            return {
                "status": "error",
                "location_id": location_id,
                "error": "Delete failed",
            }

    except Exception as e:
        logger.error(f"Error in delete_location_from_firebase_task: {str(e)}")
        return {"status": "error", "location_id": location_id, "error": str(e)}


@celery_app.task(name="check_preparation_timeout")
def check_preparation_timeout_task(reservation_id: str) -> dict:
    """
    Check if preparation time (20 minutes) has expired for a reservation.
    This task should be scheduled to run after the preparation deadline.
    """
    try:
        from apps.core.constants import (
            RESERVATION_STATUS_CANCELLED,
            UNIT_STATUS_AVAILABLE,
        )
        from apps.core.database import get_session
        from apps.lockers import crud
        from apps.lockers.services import get_locker_status_service
        from apps.lockers.timing import is_preparation_expired

        db_gen = get_session()
        db: Session = next(db_gen)
        try:
            reservation = crud.get_locker_reservation_by_id(db, reservation_id)
            if not reservation:
                db.close()
                return {"status": "error", "message": "Reservation not found"}

            locker_unit = get_locker_unit_by_id(db, reservation.locker_unit_id)
            if not locker_unit:
                db.close()
                return {"status": "error", "message": "Locker unit not found"}

            # Check if combo was already placed
            if reservation.item_deposited_at:
                db.close()
                return {
                    "status": "success",
                    "message": "Combo was already placed in time",
                }

            # Check Galilei hardware status to see if shop deposited item
            valid_status_found = False
            pickup_datetime = None

            if reservation.created_at and reservation.preparation_deadline:
                from apps.lockers.services import verify_galilei_door_activity

                from_date_jst = (
                    reservation.created_at + timedelta(hours=9)
                ).strftime("%Y%m%d%H%M%S")
                to_date_jst = (
                    reservation.preparation_deadline + timedelta(hours=9)
                ).strftime("%Y%m%d%H%M%S")

                valid_status_found, pickup_datetime = verify_galilei_door_activity(
                    locker_unit=locker_unit,
                    access_code=reservation.access_code,
                    from_date=from_date_jst,
                    to_date=to_date_jst,
                    put_in=True,
                )
            else:
                logger.warning(
                    f"Reservation {reservation_id} missing created_at or preparation_deadline"
                )

            if valid_status_found and pickup_datetime:
                # Update reservation status and deposit time
                reservation.status = RESERVATION_STATUS_ACTIVE
                reservation.item_deposited_at = pickup_datetime

                # Update locker unit status to occupied using CRUD (handles commit)
                crud.update_locker_unit(
                    db, locker_unit.id, {"status": UNIT_STATUS_OCCUPIED}
                )

                # Handle combo activation and timing
                from apps.lockers.utils import handle_combo_activation
                handle_combo_activation(db, reservation, reservation_id)

                # Commit all changes
                db.commit()

                # Sync unit status to Firebase
                if locker_unit.id:
                    sync_location_to_firebase_task.delay(
                        str(locker_unit.id), is_unit_id=True
                    )

                logger.info(
                    f"Reservation {reservation_id}: Item was deposited at {pickup_datetime}"
                )
                db.close()
                return {"status": "success", "message": "Combo was placed in time"}

            # Check if preparation time expired
            if (
                reservation.preparation_deadline
                and reservation.status == RESERVATION_STATUS_PENDING
                and is_preparation_expired(reservation.preparation_deadline)
            ):
                # Update reservation status to cancelled
                crud.update_locker_reservation(
                    db, reservation_id, {"status": RESERVATION_STATUS_CANCELLED}
                )

                # Free up the locker unit
                if reservation.unit:
                    crud.update_locker_unit(
                        db,
                        reservation.unit.id,
                        {"status": UNIT_STATUS_AVAILABLE},
                    )

                # Update combo status if exists
                if reservation.combo:
                    reservation.combo.status = COMBO_STATUS_EXPIRED_PUT_IN_LOCKER

                # Create cooldown for the shop
                from apps.lockers.models.shop_cooldown import ShopCooldown
                from apps.lockers.timing import create_shop_cooldown

                cooldown_end = create_shop_cooldown(reservation.shop_id, reservation.id)
                shop_cooldown = ShopCooldown(
                    shop_id=reservation.shop_id,
                    failed_reservation_id=reservation.id,
                    cooldown_end=cooldown_end,
                    reason="preparation_timeout",
                )
                db.add(shop_cooldown)

                db.commit()

                # Remove AA code from Galilei system (shop put-in code is no longer valid)
                if reservation.unit is not None:
                    from apps.lockers.services import _remove_galilei_code
                    _remove_galilei_code(reservation.unit, put_in=True)

                # Explicitly sync to Firebase after unit status update
                if reservation.unit:
                    sync_location_to_firebase_task.delay(
                        str(reservation.unit.id), is_unit_id=True
                    )

                # Only reset the access code if there are no other active reservations for this unit
                from apps.lockers.models.reservation import LockerReservation

                active_reservations = db.exec(
                    select(LockerReservation).where(
                        LockerReservation.locker_unit_id == reservation.locker_unit_id,
                        LockerReservation.status == RESERVATION_STATUS_ACTIVE,
                    )
                ).all()

                if not active_reservations:
                    from apps.lockers.services import _remove_galilei_code

                    _remove_galilei_code(reservation.unit, put_in=True)
                    logger.info(
                        f"Reset access code for unit {reservation.unit.unit_number} - no active reservations"
                    )
                else:
                    logger.info(
                        f"Skipped resetting access code for unit {reservation.unit.unit_number} - "
                        f"{len(active_reservations)} active reservations exist"
                    )

                # Check and update Firebase shop combo count if criteria are met
                from apps.products.utils import sync_shop_combo_count_to_firebase, count_shop_pending_combos

                combo_count = count_shop_pending_combos(db, reservation.shop_id)
                sync_shop_combo_count_to_firebase(reservation.shop_id, combo_count)

                logger.info(
                    f"Preparation timeout: Shop {reservation.shop_id} cooldown until {cooldown_end}"
                )
                db.close()
                return {
                    "status": "success",
                    "message": "Reservation cancelled and shop cooldown applied",
                }

            return {"status": "success", "message": "Preparation time not yet expired"}

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error in check_preparation_timeout_task: {str(e)}")
        return {"status": "error", "error": str(e)}
