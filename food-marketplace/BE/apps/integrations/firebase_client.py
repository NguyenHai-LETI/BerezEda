import logging
from typing import Optional

from apps.core.config import (
    GOOGLE_APPLICATION_CREDENTIALS,
    FIREBASE_PROJECT_ID,
    FIRESTORE_DATABASE_ID,
)

logger = logging.getLogger(__name__)


class FirebaseService:
    _initialized = False
    _db = None
    _app = None

    @classmethod
    def _bypass_proxy(cls) -> None:
        import os
        # Firebase SDK (via google-auth + requests) picks up system HTTPS_PROXY env var.
        # If the local proxy (e.g. Clash/V2Ray) is not running, every Google API call fails.
        # Add googleapis.com to NO_PROXY so requests skips the proxy for these hosts.
        google_hosts = "googleapis.com,oauth2.googleapis.com,firestore.googleapis.com,fcm.googleapis.com"
        for key in ("NO_PROXY", "no_proxy"):
            current = os.environ.get(key, "")
            if "googleapis.com" not in current:
                os.environ[key] = f"{current},{google_hosts}".lstrip(",")

    @classmethod
    def init(cls) -> bool:
        if cls._initialized:
            return True
        if not GOOGLE_APPLICATION_CREDENTIALS or not FIREBASE_PROJECT_ID:
            logger.warning("Firebase not configured — running without Firebase")
            return False
        cls._bypass_proxy()
        try:
            import firebase_admin
            from firebase_admin import credentials, firestore
            if not firebase_admin._apps:
                cred = credentials.Certificate(GOOGLE_APPLICATION_CREDENTIALS)
                cls._app = firebase_admin.initialize_app(cred, {"projectId": FIREBASE_PROJECT_ID})
            cls._db = firestore.client(database_id=FIRESTORE_DATABASE_ID)
            cls._initialized = True
            logger.info("Firebase initialized")
            return True
        except Exception as e:
            logger.error(f"Firebase init failed: {e}")
            return False

    @classmethod
    def get_db(cls):
        if not cls._initialized:
            cls.init()
        return cls._db

    @classmethod
    def sync_locker_location(cls, location_id: str, data: dict) -> None:
        db = cls.get_db()
        if not db:
            return
        try:
            db.collection("locker_locations").document(location_id).set(data, merge=True)
        except Exception as e:
            logger.error(f"Firebase sync locker failed: {e}")

    @classmethod
    def sync_locker_unit(cls, location_id: str, unit_id: str, data: dict) -> None:
        db = cls.get_db()
        if not db:
            return
        try:
            (
                db.collection("locker_locations")
                .document(location_id)
                .collection("units")
                .document(unit_id)
                .set(data, merge=True)
            )
        except Exception as e:
            logger.error(f"Firebase sync unit failed: {e}")

    @classmethod
    def sync_combo(cls, combo_id: str, data: dict) -> None:
        db = cls.get_db()
        if not db:
            return
        try:
            db.collection("combos").document(combo_id).set(data, merge=True)
        except Exception as e:
            logger.error(f"Firebase sync combo failed: {e}")

    @classmethod
    def delete_combo(cls, combo_id: str) -> None:
        db = cls.get_db()
        if not db:
            return
        try:
            db.collection("combos").document(combo_id).delete()
        except Exception as e:
            logger.error(f"Firebase delete combo failed: {e}")

    @classmethod
    def send_push(cls, token: str, title: str, body: str, data: Optional[dict] = None) -> bool:
        if not cls._initialized:
            cls.init()
        try:
            from firebase_admin import messaging
            msg = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data={k: str(v) for k, v in (data or {}).items()},
                token=token,
                webpush=messaging.WebpushConfig(
                    notification=messaging.WebpushNotification(title=title, body=body),
                ),
            )
            messaging.send(msg)
            return True
        except Exception as e:
            err_str = str(e)
            if "NotRegistered" in err_str or "InvalidRegistration" in err_str:
                logger.warning(f"FCM token expired, deactivating: {token[:20]}...")
                cls._deactivate_token(token)
            else:
                logger.error(f"FCM push failed for token {token[:20]}...: {e}")
            return False

    @classmethod
    def _deactivate_token(cls, token: str):
        try:
            from apps.core.database import get_sync_session
            from apps.devices.crud import deactivate_token
            with get_sync_session() as db:
                from apps.devices.models import Device
                from sqlmodel import select
                device = db.exec(select(Device).where(Device.fcm_token == token)).first()
                if device:
                    device.is_active = False
                    db.add(device)
                    db.commit()
        except Exception as e:
            logger.error(f"Failed to deactivate token: {e}")

    @classmethod
    def send_push_multicast(cls, tokens: list, title: str, body: str, data: Optional[dict] = None) -> int:
        if not tokens:
            return 0
        if not cls._initialized:
            cls.init()
        success = 0
        for token in tokens:
            if cls.send_push(token, title, body, data):
                success += 1
        return success


firebase_service = FirebaseService()
