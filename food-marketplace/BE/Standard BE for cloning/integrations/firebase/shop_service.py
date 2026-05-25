from datetime import datetime
from typing import Any, Dict, Optional

from apps.core.logging import logger
from apps.integrations.firebase.client import get_firestore_client
from apps.shops.models.shops import Shop


class FirebaseShopService:
    """Service for syncing shop data with Firebase."""

    def __init__(self):
        self.client = get_firestore_client()
        self.collection_name = "shops"

    def _shop_to_dict(self, shop: Shop, db_session=None) -> Dict[str, Any]:
        """Convert Shop model to dictionary for Firebase storage."""
        shop_data = {
            "id": str(shop.id),
            "code": shop.code,
            "name": shop.name,
            "avg_rating": float(shop.avg_rating) if shop.avg_rating else 0.0,
            "total_reviews": int(shop.total_reviews) if shop.total_reviews else 0,
            "total_revenue_this_month": 0.0,
            "is_active": shop.is_active,
            "created_at": shop.created_at.isoformat() if shop.created_at else None,
            "updated_at": shop.updated_at.isoformat() if shop.updated_at else None,
            "sync_timestamp": datetime.utcnow().isoformat(),
        }

        # Add owner information if available
        if shop.owner_id:
            shop_data["owner_id"] = str(shop.owner_id)

        # Add analytics data if database session is provided
        if db_session:
            try:
                from apps.shops.analytics import get_shop_analytics_for_firebase

                analytics = get_shop_analytics_for_firebase(db_session, str(shop.id))
                shop_data.update(analytics)
            except Exception as e:
                logger.warning(f"Failed to get analytics for shop {shop.id}: {e}")

        return shop_data

    def sync_shop_data_to_firebase(self, shop_data: Dict[str, Any]) -> bool:
        """Sync shop data (as dictionary) to Firebase."""
        try:
            if not self.client:
                logger.error("Firebase client not initialized")
                return False

            shop_id = shop_data.get("id")
            if not shop_id:
                logger.error("Shop ID is required for Firebase sync")
                return False

            # Reference to the shop document
            doc_ref = self.client.collection(self.collection_name).document(
                str(shop_id)
            )

            # Set the document with the shop data
            doc_ref.set(shop_data)

            logger.info(f"Successfully synced shop {shop_id} to Firebase")
            return True

        except Exception as e:
            logger.error(f"Failed to sync shop to Firebase: {e}")
            return False

    async def sync_shop_to_firebase(self, shop: Shop, db_session=None) -> bool:
        """Convert Shop model to dict and sync to Firebase."""
        try:
            shop_data = self._shop_to_dict(shop, db_session)
            return self.sync_shop_data_to_firebase(shop_data)

        except Exception as e:
            logger.error(
                f"Failed to convert shop {shop.id} to dict for Firebase sync: {e}"
            )
            return False

    def update_shop_in_firebase(
        self, shop_id: str, update_data: Dict[str, Any]
    ) -> bool:
        """Update specific fields of a shop in Firebase."""
        try:
            if not self.client:
                logger.error("Firebase client not initialized")
                return False

            # Add update timestamp
            update_data["sync_timestamp"] = datetime.utcnow().isoformat()

            # Reference to the shop document
            doc_ref = self.client.collection(self.collection_name).document(
                str(shop_id)
            )

            # Update the document with partial data
            doc_ref.update(update_data)

            logger.info(f"Successfully updated shop {shop_id} in Firebase")
            return True

        except Exception as e:
            logger.error(f"Failed to update shop {shop_id} in Firebase: {e}")
            return False

    def delete_shop_from_firebase(self, shop_id: str) -> bool:
        """Delete a shop from Firebase."""
        try:
            if not self.client:
                logger.error("Firebase client not initialized")
                return False

            # Reference to the shop document
            doc_ref = self.client.collection(self.collection_name).document(
                str(shop_id)
            )

            # Delete the document
            doc_ref.delete()

            logger.info(f"Successfully deleted shop {shop_id} from Firebase")
            return True

        except Exception as e:
            logger.error(f"Failed to delete shop {shop_id} from Firebase: {e}")
            return False

    def get_shop_from_firebase(self, shop_id: str) -> Optional[Dict[str, Any]]:
        """Get shop data from Firebase."""
        try:
            if not self.client:
                logger.error("Firebase client not initialized")
                return None

            # Reference to the shop document
            doc_ref = self.client.collection(self.collection_name).document(
                str(shop_id)
            )
            doc = doc_ref.get()

            if doc.exists:
                return doc.to_dict()
            else:
                logger.warning(f"Shop {shop_id} not found in Firebase")
                return None

        except Exception as e:
            logger.error(f"Failed to get shop {shop_id} from Firebase: {e}")
            return None
