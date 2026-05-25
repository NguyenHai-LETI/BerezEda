from typing import Optional

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1 import Client as FirestoreClient

from apps.core.logging import logger
from apps.integrations.firebase.config import get_firebase_credentials

# Global Firebase app instance
_firebase_app: Optional[firebase_admin.App] = None
_firestore_client: Optional[FirestoreClient] = None


def initialize_firebase() -> Optional[firebase_admin.App]:
    """Initialize Firebase app with service account credentials."""
    global _firebase_app

    if _firebase_app is not None:
        return _firebase_app

    try:
        creds = get_firebase_credentials()
        if not creds:
            logger.warning(
                "Firebase credentials not found. Check if firebase-service-account.json exists and GOOGLE_APPLICATION_CREDENTIALS is set correctly"
            )
            return None

        # Initialize Firebase with service account credentials
        cred = credentials.Certificate(creds)
        _firebase_app = firebase_admin.initialize_app(cred)

        logger.info("Firebase initialized successfully")
        return _firebase_app

    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {str(e)}")
        return None


def get_firestore_client() -> Optional[FirestoreClient]:
    """Get Firestore client instance."""
    global _firestore_client

    if _firestore_client is not None:
        return _firestore_client

    try:
        app = initialize_firebase()
        if not app:
            return None

        _firestore_client = firestore.client(app)
        logger.info("Firestore client initialized successfully")
        return _firestore_client

    except Exception as e:
        logger.error(f"Failed to initialize Firestore client: {str(e)}")
        return None


def test_firebase_connection() -> bool:
    """Test Firebase connection by attempting to read from Firestore."""
    try:
        client = get_firestore_client()
        if not client:
            return False

        # Try to read a test collection
        test_ref = client.collection("test").limit(1)
        list(test_ref.stream())  # This will fail if connection is bad

        logger.info("Firebase connection test successful")
        return True

    except Exception as e:
        logger.error(f"Firebase connection test failed: {str(e)}")
        return False
