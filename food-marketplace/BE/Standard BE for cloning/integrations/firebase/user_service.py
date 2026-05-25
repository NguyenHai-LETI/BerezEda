from datetime import datetime
from typing import Any, Dict, Optional

from apps.core.logging import logger
from apps.integrations.firebase.client import get_firestore_client
from apps.users.models.users import User


class FirebaseUserService:
    """Service for syncing user data with Firebase."""

    def __init__(self):
        self.client = get_firestore_client()
        self.collection_name = "users"

    def _user_to_dict(self, user: User) -> Dict[str, Any]:
        """Convert User model to dictionary for Firebase storage."""
        user_data = {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "permissions": user.permissions,
            "phone": user.phone,
            "is_active": user.is_active,
            "code_shop": user.code_shop,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "sync_timestamp": datetime.utcnow().isoformat(),
        }

        # Add optional fields if they exist
        optional_fields = [
            "username",
            "first_name",
            "last_name",
            "date_of_birth",
            "address",
        ]
        for field in optional_fields:
            if hasattr(user, field) and getattr(user, field) is not None:
                user_data[field] = getattr(user, field)
                if field == "date_of_birth" and isinstance(user_data[field], datetime):
                    user_data[field] = user_data[field].isoformat()

        return user_data

    def sync_user_data_to_firebase(self, user_data: Dict[str, Any]) -> bool:
        """
        Sync user data to Firebase using pre-extracted data.

        Args:
            user_data: Dictionary containing user data

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.client:
            logger.error("Firebase client not available for user sync")
            return False

        try:
            user_id = user_data.get("id")
            if not user_id:
                logger.error("User ID not found in user data for Firebase sync")
                return False

            # Reference to the user document
            doc_ref = self.client.collection(self.collection_name).document(user_id)

            # Set/update the user data
            doc_ref.set(user_data, merge=True)

            logger.info(f"Successfully synced user {user_id} to Firebase")
            return True

        except Exception as e:
            logger.error(f"Error syncing user data to Firebase: {e}")
            return False

    def sync_user_to_firebase(self, user: User) -> bool:
        """
        Sync user object to Firebase.

        Args:
            user: User object to sync

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            user_data = self._user_to_dict(user)
            return self.sync_user_data_to_firebase(user_data)
        except Exception as e:
            logger.error(f"Error converting user to dict for Firebase sync: {e}")
            return False

    def update_user_in_firebase(
        self, user_id: str, update_data: Dict[str, Any]
    ) -> bool:
        """
        Update specific fields of a user in Firebase.

        Args:
            user_id: User ID to update
            update_data: Dictionary of fields to update

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.client:
            logger.error("Firebase client not available for user update")
            return False

        try:
            # Add sync timestamp
            update_data["sync_timestamp"] = datetime.utcnow().isoformat()

            # Reference to the user document
            doc_ref = self.client.collection(self.collection_name).document(user_id)

            # Update the user data
            doc_ref.update(update_data)

            logger.info(f"Successfully updated user {user_id} in Firebase")
            return True

        except Exception as e:
            logger.error(f"Error updating user {user_id} in Firebase: {e}")
            return False

    def delete_user_from_firebase(self, user_id: str) -> bool:
        """
        Delete user from Firebase.

        Args:
            user_id: User ID to delete

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.client:
            logger.error("Firebase client not available for user deletion")
            return False

        try:
            # Reference to the user document
            doc_ref = self.client.collection(self.collection_name).document(user_id)

            # Delete the user document
            doc_ref.delete()

            logger.info(f"Successfully deleted user {user_id} from Firebase")
            return True

        except Exception as e:
            logger.error(f"Error deleting user {user_id} from Firebase: {e}")
            return False

    def get_user_from_firebase(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user data from Firebase.

        Args:
            user_id: User ID to retrieve

        Returns:
            Dict containing user data or None if not found/error
        """
        if not self.client:
            logger.error("Firebase client not available for user retrieval")
            return None

        try:
            # Reference to the user document
            doc_ref = self.client.collection(self.collection_name).document(user_id)
            doc = doc_ref.get()

            if doc.exists:
                logger.info(f"Successfully retrieved user {user_id} from Firebase")
                return doc.to_dict()
            else:
                logger.warning(f"User {user_id} not found in Firebase")
                return None

        except Exception as e:
            logger.error(f"Error retrieving user {user_id} from Firebase: {e}")
            return None
