from datetime import datetime
from typing import Any, Dict, Optional

from apps.core.logging import logger
from apps.core.utils import format_datetime_for_firebase
from apps.integrations.firebase.client import get_firestore_client
from apps.products.models import Combo


class FirebaseComboService:
    """Service for syncing combo data with Firebase."""

    def __init__(self):
        self.client = get_firestore_client()
        self.collection_name = (
            "shop_latest_combos"  # Changed to reflect one record per shop
        )

    def _combo_to_dict(self, combo: Combo) -> Dict[str, Any]:
        """Convert Combo model to simplified dictionary for Firebase storage."""
        try:
            # Base combo data with minimal fields
            combo_data = {
                "id": str(combo.id),
                "shop_id": str(combo.shop_id),
                "created_at": format_datetime_for_firebase(combo.created_at),
                "updated_at": format_datetime_for_firebase(combo.updated_at),
                "sync_time": format_datetime_for_firebase(datetime.utcnow()),
            }

            # Get locker information through reservation
            locker_info = self._get_locker_info(combo)
            if locker_info:
                combo_data.update(locker_info)

            return combo_data

        except Exception as e:
            logger.error(
                f"Failed to convert combo {combo.id} to dict for Firebase sync: {e}"
            )
            raise

    def _get_locker_info(self, combo: Combo) -> Optional[Dict[str, Any]]:
        """Get locker information for the combo."""
        try:
            # Import all necessary models to avoid circular dependencies
            from sqlmodel import select

            import apps.devices.models
            import apps.favorites.models
            import apps.lockers.models
            import apps.mynaportal.models  # MynaAuthorizer models
            import apps.orders.models  # Order models
            import apps.products.models
            import apps.purchase.models  # Purchase models
            import apps.reviews.models  # Review models
            from apps.core.database import get_session
            from apps.lockers.models.location import LockerLocation
            from apps.lockers.models.reservation import LockerReservation
            from apps.lockers.models.unit import LockerUnit

            # Use next() to get the session from the generator
            db = next(get_session())
            try:
                # Find the reservation for this combo
                reservation_statement = select(LockerReservation).where(
                    LockerReservation.combo_id == combo.id
                )
                reservation = db.exec(reservation_statement).first()

                if not reservation:
                    return None

                # Get the locker unit
                unit_statement = select(LockerUnit).where(
                    LockerUnit.id == reservation.locker_unit_id
                )
                unit = db.exec(unit_statement).first()

                if not unit:
                    return None

                # Get the locker location
                location_statement = select(LockerLocation).where(
                    LockerLocation.id == unit.location_id
                )
                location = db.exec(location_statement).first()
                return {
                    "locker_name": location.name if location else None,
                    "locker_address": location.address if location else None,
                    "unit_number": unit.unit_number,
                    "sale_end_time": format_datetime_for_firebase(
                        reservation.sale_end_time
                    ),
                }

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Failed to get locker info for combo {combo.id}: {e}")
            return None

    def _is_newest_combo_for_shop(self, combo: Combo) -> bool:
        """Check if this combo is the newest for its shop."""
        try:
            # Import all necessary models to avoid circular dependencies
            from sqlmodel import desc, select

            import apps.devices.models
            import apps.favorites.models
            import apps.lockers.models
            import apps.mynaportal.models  # MynaAuthorizer models
            import apps.orders.models  # Order models
            import apps.products.models
            import apps.purchase.models  # Purchase models
            import apps.reviews.models  # Review models
            from apps.core.database import get_session

            # Use next() to get the session from the generator
            db = next(get_session())
            try:
                # Get the newest combo for this shop
                statement = (
                    select(Combo)
                    .where(Combo.shop_id == combo.shop_id)
                    .order_by(desc(Combo.created_at))
                    .limit(1)
                )

                newest_combo = db.exec(statement).first()

                # Check if this combo is the newest one
                return newest_combo is not None and newest_combo.id == combo.id

            finally:
                db.close()

        except Exception as e:
            logger.error(
                f"Failed to check if combo {combo.id} is newest for shop {combo.shop_id}: {e}"
            )
            return False

    def sync_combo(self, combo: Combo) -> bool:
        """Sync a combo to Firebase - only keeps the latest combo per shop."""
        try:
            if not combo.id or not combo.shop_id:
                logger.error("Combo ID and shop_id are required for Firebase sync")
                return False

            # Check if this is the newest combo for the shop
            if not self._is_newest_combo_for_shop(combo):
                logger.info(
                    f"Combo {combo.id} is not the newest for shop {combo.shop_id}, skipping Firebase sync"
                )
                return True  # Return True as this is expected behavior

            combo_data = self._combo_to_dict(combo)
            # Use shop_id as document ID to ensure only one record per shop
            doc_ref = self.client.collection(self.collection_name).document(
                str(combo.shop_id)
            )
            doc_ref.set(combo_data)

            logger.info(
                f"Successfully synced newest combo {combo.id} for shop {combo.shop_id} to Firebase"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to sync combo {combo.id} to Firebase: {e}")
            return False

    def delete_combo_for_shop(self, shop_id: str) -> bool:
        """Delete the combo record for a shop from Firebase."""
        try:
            doc_ref = self.client.collection(self.collection_name).document(shop_id)
            doc_ref.delete()

            logger.info(
                f"Successfully deleted combo record for shop {shop_id} from Firebase"
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to delete combo record for shop {shop_id} from Firebase: {e}"
            )
            return False

    def get_shop_latest_combo(self, shop_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest combo for a shop from Firebase."""
        try:
            doc_ref = self.client.collection(self.collection_name).document(shop_id)
            doc = doc_ref.get()

            if doc.exists:
                return doc.to_dict()
            return None

        except Exception as e:
            logger.error(
                f"Failed to get latest combo for shop {shop_id} from Firebase: {e}"
            )
            return None

    def sync_shop_latest_combo(self, shop_id: str) -> bool:
        """Sync only the latest combo for a specific shop to Firebase."""
        try:
            # Import all necessary models to avoid circular dependencies
            from sqlmodel import desc, select

            import apps.devices.models
            import apps.favorites.models
            import apps.lockers.models
            import apps.mynaportal.models  # MynaAuthorizer models
            import apps.orders.models  # Order models
            import apps.products.models
            import apps.purchase.models  # Purchase models
            import apps.reviews.models  # Review models
            from apps.core.database import get_session

            # Use next() to get the session from the generator
            db = next(get_session())
            try:
                # Query only the newest combo for the shop
                statement = (
                    select(Combo)
                    .where(Combo.shop_id == shop_id)
                    .order_by(desc(Combo.created_at))
                    .limit(1)
                )

                newest_combo = db.exec(statement).first()

                if newest_combo:
                    success = self.sync_combo(newest_combo)
                    if success:
                        logger.info(
                            f"Successfully synced latest combo {newest_combo.id} for shop {shop_id} to Firebase"
                        )
                    return success
                else:
                    logger.info(f"No combos found for shop {shop_id}")
                    return True

            finally:
                db.close()

        except Exception as e:
            logger.error(
                f"Failed to sync latest combo for shop {shop_id} to Firebase: {e}"
            )
            return False
