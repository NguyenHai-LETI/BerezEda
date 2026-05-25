import logging
from datetime import datetime

from sqlmodel import Session, select

from apps.core.celery_app import celery_app
from apps.core.database import engine
from apps.core.utils import get_current_time
from apps.notifications.services.to_user import (
    handle_new_combo_published,
    send_combo_pickup_deadline_approaching_notification,
    send_order_canceled_notification,
    send_product_expiry_reached_notification,
)


@celery_app.task
def send_favorite_shop_add_new_combo(combo_id: str, shop_id: str):
    """Task to send notifications to users who favorited a store when it publishes new combo"""
    try:
        handle_new_combo_published(combo_id, shop_id)
        logging.info(
            f"Successfully sent favorite shop combo notifications for combo {combo_id}"
        )
    except Exception as e:
        logging.error(f"Error sending favorite shop combo notifications: {e}")


@celery_app.task
def send_combo_cancelled(combo_id: str, buyer_id: str):
    """Task to send combo cancellation notifications to both buyer and store"""
    try:
        # Notify buyer about refund
        send_order_canceled_notification(combo_id, buyer_id)
        logging.info(
            f"Successfully sent combo cancellation notifications for combo {combo_id}"
        )
    except Exception as e:
        logging.error(f"Error sending combo cancellation notifications: {e}")


@celery_app.task
def send_pickup_deadline(combo_id: str, user_id: str):
    """Task to send pickup deadline approaching notification to buyer (5 minutes before)"""
    try:
        send_combo_pickup_deadline_approaching_notification(combo_id, user_id)
        logging.info(
            f"Successfully sent pickup deadline approaching notification for combo {combo_id} to user {user_id}"
        )
    except Exception as e:
        logging.error(f"Error sending pickup deadline approaching notification: {e}")


@celery_app.task
def schedule_product_expiry_notifications(combo_id: str, user_id: str):
    """
    Task A: Fires 2 seconds after order becomes PICKED_UP.
    Queries combo_products and schedules individual notifications at each expiry_date.
    """
    from apps.products.models import Combo

    try:
        with Session(engine) as session:
            combo = session.exec(select(Combo).where(Combo.id == combo_id)).first()

            if not combo:
                logging.warning(
                    f"Combo {combo_id} not found for scheduling expiry notifications"
                )
                return

            current_time = get_current_time()
            scheduled_count = 0

            for combo_product in combo.combo_products:
                if not combo_product.expiry_dates:
                    continue

                for expiry_date_str in combo_product.expiry_dates:
                    try:
                        if isinstance(expiry_date_str, str):
                            expiry_date = datetime.fromisoformat(expiry_date_str)
                        else:
                            expiry_date = expiry_date_str

                        # Only schedule if expiry_date is in the future
                        if expiry_date > current_time:
                            send_product_expiry_reached.apply_async(
                                args=[combo_id, user_id, str(combo_product.id)],
                                eta=expiry_date,
                            )
                            scheduled_count += 1
                            logging.info(
                                f"Scheduled expiry notification for combo {combo_id} at {expiry_date}"
                            )
                    except (ValueError, TypeError) as e:
                        logging.warning(
                            f"Failed to parse expiry date '{expiry_date_str}' "
                            f"for combo_product {combo_product.id}: {e}"
                        )
                        continue

            logging.info(
                f"Scheduled {scheduled_count} expiry notifications for combo {combo_id}"
            )

    except Exception as e:
        logging.error(
            f"Error scheduling product expiry notifications for combo {combo_id}: {e}"
        )


@celery_app.task
def send_product_expiry_reached(combo_id: str, user_id: str, combo_product_id: str):
    """
    Task B: Fires at exact expiry_date time.
    Sends push notification asking buyer about product consumption status.
    One notification per combo_product (each combo_product can have different expiry_date).
    """
    try:
        send_product_expiry_reached_notification(combo_id, user_id, combo_product_id)
        logging.info(
            f"Successfully sent product expiry reached notification "
            f"for combo {combo_id} to user {user_id}"
        )
    except Exception as e:
        logging.error(
            f"Error sending product expiry reached notification "
            f"for combo {combo_id}: {e}"
        )
