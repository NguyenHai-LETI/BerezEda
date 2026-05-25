import json
import os
from typing import Optional

# Firebase configuration using JSON file path
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "")

# Firestore database configuration
FIRESTORE_DATABASE_ID = os.getenv("FIRESTORE_DATABASE_ID", "(default)")

# Firebase Realtime Database URL (if using Realtime Database instead of Firestore)
FIREBASE_DATABASE_URL = os.getenv("FIREBASE_DATABASE_URL", "")


def get_firebase_credentials() -> Optional[dict]:
    """Get Firebase service account credentials from JSON file."""
    if not GOOGLE_APPLICATION_CREDENTIALS:
        return None

    if not os.path.exists(GOOGLE_APPLICATION_CREDENTIALS):
        return None

    try:
        # Load credentials from JSON file
        with open(GOOGLE_APPLICATION_CREDENTIALS, "r") as f:
            credentials = json.load(f)

        # Validate that required fields are present
        required_fields = ["type", "project_id", "private_key", "client_email"]
        missing_fields = [
            field for field in required_fields if field not in credentials
        ]

        if missing_fields:
            return None

        return credentials

    except (FileNotFoundError, json.JSONDecodeError) as e:
        return None
