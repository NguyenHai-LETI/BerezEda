from datetime import datetime
from typing import Any, Dict, List

from apps.core.constants import COMBO_STATUS_SELLING
from apps.core.logging import logger
from apps.integrations.firebase.client import get_firestore_client
from apps.lockers.models.location import LockerLocation
from apps.lockers.models.unit import LockerUnit


class FirebaseLockerService:
    """Service for syncing locker location data with embedded units to Firebase."""

    def __init__(self):
        self.client = get_firestore_client()
        self.collection_name = "locker_locations"

    def _location_to_dict(
        self, location: LockerLocation, units: List[LockerUnit]
    ) -> Dict[str, Any]:
        """Convert LockerLocation with units to dictionary for Firebase storage."""

        # Convert units to simplified format
        units_data = []
        for unit in units:
            # Get the latest active reservation's sale_end_time if exists
            sale_end_time = None
            if hasattr(unit, "reservations") and unit.reservations:
                # Import constant for active status
                from apps.core.constants import RESERVATION_STATUS_ACTIVE

                # Filter active reservations with selling combos
                active_reservations = [
                    r
                    for r in unit.reservations
                    if r.status == RESERVATION_STATUS_ACTIVE
                    and r.combo
                    and r.combo.status == COMBO_STATUS_SELLING
                ]

                # Get the newest reservation by item_deposited_at (or created_at as fallback)
                if active_reservations:
                    active_reservation = max(
                        active_reservations,
                        key=lambda r: r.item_deposited_at or r.created_at,
                    )
                    if active_reservation.sale_end_time:
                        sale_end_time = active_reservation.sale_end_time.isoformat()
                else:
                    sale_end_time = None

            unit_data = {
                "id": str(unit.id),
                "unit_number": unit.unit_number,
                "temperature": unit.temperature,  # Added temperature field
                "status": unit.status,
                "size": unit.size,
                "is_active": unit.is_active,
                "sale_end_time": sale_end_time,
            }
            units_data.append(unit_data)

        # Convert associated shops to list of shop IDs
        shop_ids = []
        try:
            # First try to use shops loaded specifically for sync
            shops_for_sync = getattr(location, "_shops_for_sync", None)
            if shops_for_sync:
                shop_ids = [str(shop.id) for shop in shops_for_sync]
            # Fallback to normal shops relationship
            elif hasattr(location, "shops") and location.shops:
                shop_ids = [str(shop.id) for shop in location.shops]
        except Exception:
            # If shops relationship is not loaded or causes an error,
            # we'll sync without shop information
            shop_ids = []

        location_data = {
            "id": str(location.id),
            "name": location.name,
            "address": location.address,
            "position": location.position,
            "units": units_data,
            "shop_ids": shop_ids,  # Changed from shop_id to shop_ids array
            "created_at": (
                location.created_at.isoformat() if location.created_at else None
            ),
            "updated_at": (
                location.updated_at.isoformat() if location.updated_at else None
            ),
            "sync_time": datetime.utcnow().isoformat(),
        }

        return location_data

    def sync_location_to_firebase(
        self, location: LockerLocation, units: List[LockerUnit]
    ) -> bool:
        """Sync a locker location with its units to Firebase."""
        if not self.client:
            logger.warning("Firebase client not available, skipping location sync")
            return False

        try:
            location_data = self._location_to_dict(location, units)
            doc_ref = self.client.collection(self.collection_name).document(
                str(location.id)
            )
            doc_ref.set(location_data)

            logger.info(
                f"Successfully synced location {location.id} with {len(units)} units to Firebase"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to sync location {location.id} to Firebase: {str(e)}")
            return False

    def sync_single_unit_to_firebase(self, location_id: str, unit: LockerUnit) -> bool:
        """Update a single unit in Firebase without affecting other units."""
        if not self.client:
            logger.warning("Firebase client not available, skipping unit sync")
            return False

        try:
            # Convert the single unit to dict format
            sale_end_time = None
            if hasattr(unit, "reservations") and unit.reservations:
                from apps.core.constants import RESERVATION_STATUS_ACTIVE

                # Filter active reservations with selling combos
                active_reservations = [
                    r
                    for r in unit.reservations
                    if r.status == RESERVATION_STATUS_ACTIVE
                    and r.combo
                    and r.combo.status == COMBO_STATUS_SELLING
                ]

                # Get the newest reservation by item_deposited_at (or created_at as fallback)
                if active_reservations:
                    active_reservation = max(
                        active_reservations,
                        key=lambda r: r.item_deposited_at or r.created_at,
                    )
                    if active_reservation.sale_end_time:
                        sale_end_time = active_reservation.sale_end_time.isoformat()
                else:
                    sale_end_time = None

            unit_data = {
                "id": str(unit.id),
                "unit_number": unit.unit_number,
                "temperature": unit.temperature,
                "status": unit.status,
                "size": unit.size,
                "is_active": unit.is_active,
                "sale_end_time": sale_end_time,
            }

            # Update just this unit in the units array
            doc_ref = self.client.collection(self.collection_name).document(location_id)

            # Use array operations to update the specific unit
            # First, try to read the current document
            doc = doc_ref.get()
            if not doc.exists:
                logger.warning(
                    f"Location {location_id} not found in Firebase, skipping unit update"
                )
                return False

            current_data = doc.to_dict()
            if current_data is None:
                logger.warning(
                    f"Location {location_id} has no data in Firebase, skipping unit update"
                )
                return False

            units_array = current_data.get("units", [])

            # Find and update the specific unit
            unit_updated = False
            for i, existing_unit in enumerate(units_array):
                if existing_unit.get("id") == str(unit.id):
                    units_array[i] = unit_data
                    unit_updated = True
                    break

            # If unit not found in existing units, add it
            if not unit_updated:
                units_array.append(unit_data)

            # Update the document with the modified units array and sync time
            update_data = {
                "units": units_array,
                "sync_time": datetime.utcnow().isoformat(),
            }
            doc_ref.update(update_data)

            logger.info(
                f"Successfully synced unit {unit.id} in location {location_id} to Firebase"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to sync unit {unit.id} to Firebase: {str(e)}")
            return False

    async def delete_location_from_firebase(self, location_id: str) -> bool:
        """Delete a locker location from Firebase."""
        if not self.client:
            logger.warning("Firebase client not available, skipping location deletion")
            return False

        try:
            doc_ref = self.client.collection(self.collection_name).document(location_id)
            doc_ref.delete()

            logger.info(f"Successfully deleted location {location_id} from Firebase")
            return True

        except Exception as e:
            logger.error(
                f"Failed to delete location {location_id} from Firebase: {str(e)}"
            )
            return False


# Global service instance
firebase_locker_service = FirebaseLockerService()
