import logging
from typing import Optional

from sqlmodel import Session, select

from apps.devices.models import Device
from apps.notifications.constants import NotificationType
from apps.notifications.models import Notification
from apps.users.models import User

logger = logging.getLogger(__name__)


def send_push_notification(
    session: Session,
    user: User,
    template: dict,
    combo=None,
    notification_type: Optional[NotificationType] = None,
    extra_data: Optional[dict] = None,
):
    """Send push notification and persist a record in the simple Notification table."""
    try:
        template_data = {}
        if combo:
            template_data.update({
                "product_code": getattr(combo, "product_number", None) or str(combo.id)[:8],
                "product_name": getattr(combo, "name", None) or getattr(combo, "title", None) or "Unknown",
            })
        if extra_data:
            template_data.update(extra_data)

        title = template["title"].format(**template_data) if template_data else template["title"]
        content = template["content"].format(**template_data) if template_data else template["content"]

        reference_id = str(combo.id) if combo else None

        # Persist notification in simple model (user_id direct)
        notif = Notification(
            user_id=str(user.id),
            title=title,
            body=content,
            notification_type=notification_type.value if notification_type else "info",
            reference_id=reference_id,
        )
        session.add(notif)
        session.commit()

        # Send Firebase push (best-effort)
        _send_firebase_push(session, user, title, content, notification_type, reference_id)

    except Exception as e:
        logger.error(f"send_push_notification error for user {user.id}: {e}")


def _send_firebase_push(
    session: Session,
    user: User,
    title: str,
    content: str,
    notification_type: Optional[NotificationType],
    reference_id: Optional[str],
):
    try:
        from apps.integrations.firebase.client import initialize_firebase
        firebase_app = initialize_firebase()
        if not firebase_app:
            return

        from firebase_admin import messaging

        devices = session.exec(select(Device).where(Device.user_id == str(user.id))).all()
        for device in devices:
            try:
                msg = messaging.Message(
                    notification=messaging.Notification(title=title, body=content),
                    data={
                        "type": notification_type.value if notification_type else "general",
                        "reference_id": reference_id or "",
                    },
                    android=messaging.AndroidConfig(
                        notification=messaging.AndroidNotification(sound="default")
                    ),
                    apns=messaging.APNSConfig(
                        payload=messaging.APNSPayload(aps=messaging.Aps(sound="default"))
                    ),
                    token=device.device_token,
                )
                messaging.send(msg)
                logger.info(f"Firebase push sent to user {user.id}")
            except Exception as e:
                logger.error(f"Firebase push failed for device {device.id}: {e}")
    except Exception as e:
        logger.warning(f"Firebase push skipped: {e}")
