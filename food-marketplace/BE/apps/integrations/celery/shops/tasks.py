import logging

from sqlmodel import Session

from apps.core.celery_app import celery_app
from apps.notifications.services.to_shop import (
    send_combo_cancelled,
    send_combo_pickup_completed_notification,
    send_combo_placement_deadline_approaching_notification,
    send_combo_reserved_notification,
    send_new_review_received_notification,
)


@celery_app.task
def send_user_buy_combo(combo_id: str, shop_id: str):
    """Task to send combo reservation notification to store"""
    try:
        send_combo_reserved_notification(combo_id, shop_id)
        logging.info(
            f"Successfully sent combo reservation notification for combo {combo_id}"
        )
    except Exception as e:
        logging.error(f"Error sending combo reservation notification: {e}")


@celery_app.task
def send_user_pickup(combo_id: str, shop_id: str):
    """Task to send combo pickup completed notification to store"""
    try:
        send_combo_pickup_completed_notification(combo_id, shop_id)
        logging.info(
            f"Successfully sent combo pickup completed notification for combo {combo_id}"
        )
    except Exception as e:
        logging.error(f"Error sending combo pickup completed notification: {e}")


@celery_app.task
def send_user_review(combo_id: str, user_ids: list, new_review_id: str):
    """Task to send new review notification to multiple users (owner + staff)"""
    try:
        success_count = 0
        failed_count = 0

        for user_id in user_ids:
            try:
                send_new_review_received_notification(combo_id, user_id, new_review_id)
                success_count += 1
            except Exception as e:
                logging.error(f"Failed to send notification to user {user_id}: {e}")
                failed_count += 1

        logging.info(
            f"Sent new review notifications for combo {combo_id}: {success_count} successful, {failed_count} failed"
        )
    except Exception as e:
        logging.error(f"Error sending new review notifications: {e}")


@celery_app.task
def send_deadline_put_to_locker(reservation_id: str, shop_owner_id: str):
    """Task to send placement deadline approaching notification to store (5 minutes before)"""
    try:
        send_combo_placement_deadline_approaching_notification(
            reservation_id, shop_owner_id
        )
        logging.info(
            f"Successfully sent placement deadline approaching notification for reservation {reservation_id}"
        )
    except Exception as e:
        logging.error(f"Error sending placement deadline approaching notification: {e}")


@celery_app.task
def send_user_cancelled(combo_id: str, shop_id: str):
    """Task to send combo cancellation notifications to both buyer and store"""
    try:
        # Notify buyer about refund
        send_combo_cancelled(combo_id, shop_id)
        logging.info(
            f"Successfully sent combo cancellation notifications for combo {combo_id}"
        )
    except Exception as e:
        logging.error(f"Error sending combo cancellation notifications: {e}")


@celery_app.task
def reset_monthly_shop_stats():
    """
    Task to reset monthly shop statistics on Firebase.

    Runs at 00:00 JST on the 1st of each month.
    Resets the following fields for all active shops:
    - food_loss_reduction_this_month = 0
    - free_products_this_month = 0
    - total_combo_sold_this_month = 0
    - total_revenue_this_month = 0
    """
    try:
        from datetime import timedelta, timezone

        from apps.core.database import engine
        from apps.core.utils import get_current_time
        from apps.integrations.firebase.shop_service import FirebaseShopService
        from apps.shops import crud

        # Check if it's 00:00 JST on the 1st of the month
        current_utc = get_current_time()
        jst = timezone(timedelta(hours=9))
        current_jst = current_utc.replace(tzinfo=timezone.utc).astimezone(jst)

        # Verify it's the 1st day of month and hour is 0 (00:00 JST)
        if current_jst.day != 1 or current_jst.hour != 0:
            logging.info(
                f"Skipping monthly reset - not 00:00 JST on 1st. Current JST: {current_jst}"
            )
            return {
                "status": "skipped",
                "reason": f"Not 00:00 JST on 1st. Current JST: {current_jst}",
            }

        logging.info(f"Starting monthly shop stats reset at {current_jst} (JST)")

        with Session(engine) as db:
            # Get all active shops
            shops = crud.get_all_active_shops(db)

            if not shops:
                logging.info("No active shops found to reset")
                return {"status": "success", "shops_reset": 0}

            # Prepare reset data
            reset_data = {
                "food_loss_reduction_this_month": 0,
                "free_products_this_month": 0,
                "total_combo_sold_this_month": 0,
                "total_revenue_this_month": 0,
            }

            # Update each shop in Firebase
            firebase_service = FirebaseShopService()
            success_count = 0
            failed_count = 0

            for shop in shops:
                try:
                    result = firebase_service.update_shop_in_firebase(
                        str(shop.id), reset_data
                    )
                    if result:
                        success_count += 1
                        logging.info(
                            f"Successfully reset monthly stats for shop {shop.id} ({shop.name})"
                        )
                    else:
                        failed_count += 1
                        logging.error(
                            f"Failed to reset monthly stats for shop {shop.id} ({shop.name})"
                        )
                except Exception as e:
                    failed_count += 1
                    logging.error(
                        f"Error resetting stats for shop {shop.id} ({shop.name}): {e}"
                    )

            logging.info(
                f"Monthly shop stats reset completed: {success_count} succeeded, {failed_count} failed"
            )

            return {
                "status": "success",
                "shops_reset": success_count,
                "shops_failed": failed_count,
                "total_shops": len(shops),
            }

    except Exception as e:
        logging.error(f"Error in reset_monthly_shop_stats task: {e}")
        return {"status": "error", "error": str(e)}
