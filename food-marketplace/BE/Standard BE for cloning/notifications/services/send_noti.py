import logging
from typing import Optional

from firebase_admin import messaging
from sqlmodel import Session, select

from apps.devices.models import Device
from apps.integrations.firebase.client import initialize_firebase
from apps.notifications.constants import NotificationType
from apps.notifications.models import Notification, NotificationUser
from apps.products.models import Combo
from apps.users.models import User


def send_push_notification(
    session: Session,
    user: User,
    template: dict,
    combo: Optional[Combo] = None,
    notification_type: Optional[NotificationType] = None,
    extra_data: Optional[dict] = None,
):
    """Helper function to send push notifications

    Args:
        session: Database session
        user: User to send notification to
        template: Notification template with title and content
        combo: Optional combo object for notification context
        notification_type: Type of notification
        extra_data: Additional data to format template
    """
    try:
        # Prepare template data
        template_data = {}
        if combo:
            template_data.update(
                {
                    "product_code": combo.product_number or combo.id[:8],
                    "product_name": combo.name or "Unknown Product",
                }
            )

        if extra_data:
            template_data.update(extra_data)

        # Format title and content with template data
        title = (
            template["title"].format(**template_data)
            if template_data
            else template["title"]
        )
        content = (
            template["content"].format(**template_data)
            if template_data
            else template["content"]
        )

        # Determine target_id and target_type based on notification type
        # For user notifications (not favorite store), use order_id
        # For favorite store notifications, use combo_id
        target_id = None
        target_type = "combo"

        if combo:
            # Check if this is a favorite store notification
            is_favorite_notification = (
                notification_type == NotificationType.NEW_COMBO_FROM_FAVORITE_STORE
            )
            is_review_notification = (
                notification_type == NotificationType.NEW_REVIEW_RECEIVED
            )
            is_noti_for_user = [
                NotificationType.ORDER_CANCELED,
                NotificationType.COMBO_PICKUP_DEADLINE_PASSED,
                NotificationType.PRODUCT_EXPIRED,
                NotificationType.COMBO_PICKUP_DEADLINE_APPROACHING,
            ]
            is_product_expiry_reached = (
                notification_type == NotificationType.PRODUCT_EXPIRY_REACHED
            )

            if is_product_expiry_reached:
                # For product expiry reached, use combo_product_id as target
                # so each combo_product gets its own notification
                target_id = (
                    extra_data.get("combo_product_id", combo.id)
                    if extra_data
                    else combo.id
                )
                target_type = "combo_product"

            elif is_favorite_notification:
                # For favorite notifications, use combo as target
                target_id = combo.id
                target_type = "combo"

            elif is_review_notification:
                # For review notifications, use review_id as target
                review = extra_data.get("review") if extra_data else None
                if review and hasattr(review, "id"):
                    target_id = review.id
                    target_type = "review"
                else:
                    # Fallback to combo if review not provided
                    target_id = combo.id
                    target_type = "combo"

            elif notification_type in is_noti_for_user:
                # For user order notifications, use order_id as target
                if combo.orders and len(combo.orders) > 0:
                    order = combo.orders[0]
                    order.id
                    target_id = order.id
                    target_type = "order"
                else:
                    # Fallback to combo if no order exists
                    target_id = combo.id
                    target_type = "combo"
            else:
                # For shop notifications (buy, pickup, cancel, etc.), use combo as target
                target_id = combo.id
                target_type = "combo"

        notification = Notification(
            title=title,
            body=content,
            type=Notification.INFO,
            notification_type=notification_type.value if notification_type else None,
            target_type=target_type,
            target_id=target_id,
        )
        session.add(notification)
        session.commit()
        session.refresh(notification)

        # Create notification user record
        notification_user = NotificationUser(
            notification_id=notification.id,
            user_id=user.id,
            channel=NotificationUser.PUSH,
            status=NotificationUser.PENDING,
        )
        session.add(notification_user)
        session.commit()

        # Ensure Firebase is initialized before attempting to send push notification
        firebase_app = initialize_firebase()
        if not firebase_app:
            logging.getLogger(__name__).warning(
                "Firebase not initialized - skipping push notification send"
            )
            # Mark notification user as failed since we cannot send push
            notification_user.status = NotificationUser.FAILED
            session.commit()
            return

        # Send Firebase push notification
        user_devices = session.exec(
            select(Device).where(Device.user_id == user.id)
        ).all()

        if user_devices:
            for device in user_devices:
                try:
                    # Prepare data payload
                    data_payload = {
                        "notification_id": notification.id,
                        "type": (
                            notification_type.value if notification_type else "general"
                        ),
                        "target_id": (
                            target_id if target_id else (combo.id if combo else "")
                        ),
                        "target_type": target_type,
                    }

                    # Add extra fields for specific notification types
                    if (
                        notification_type
                        in [
                            NotificationType.COMBO_PICKUP_DEADLINE_APPROACHING,
                            NotificationType.COMBO_PICKUP_DEADLINE_PASSED,
                        ]
                        and extra_data
                    ):
                        if "shop_id" in extra_data:
                            data_payload["shop_id"] = extra_data["shop_id"]
                        if "order_id" in extra_data:
                            data_payload["order_id"] = extra_data["order_id"]
                        if "order_pickup_code" in extra_data:
                            data_payload["order_pickup_code"] = extra_data[
                                "order_pickup_code"
                            ]

                    message = messaging.Message(
                        notification=messaging.Notification(title=title, body=content),
                        data=data_payload,
                        android=messaging.AndroidConfig(
                            notification=messaging.AndroidNotification(sound="default")
                        ),
                        apns=messaging.APNSConfig(
                            payload=messaging.APNSPayload(
                                aps=messaging.Aps(sound="default")
                            )
                        ),
                        token=device.device_token,
                    )

                    response = messaging.send(message)

                    # Update status to sent
                    notification_user.status = NotificationUser.SENT
                    session.commit()

                    logging.getLogger(__name__).info(
                        f"Push notification sent successfully to user {user.id}: {response}"
                    )

                except Exception as e:
                    # Update status to failed
                    notification_user.status = NotificationUser.FAILED
                    session.commit()

                    logging.getLogger(__name__).error(
                        f"Failed to send push notification to user {user.id}: {e}"
                    )

    except Exception as e:
        logging.getLogger(__name__).error(f"Error in _send_push_notification: {e}")
