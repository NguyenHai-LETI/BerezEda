import logging

from sqlmodel import Session

from apps.core.celery_app import celery_app
from apps.core.database import get_session
from apps.notifications.services.to_shop import (
    cleanup_expired_combos_and_lockers_service,
)
from apps.notifications.services.to_user import (
    send_combo_passed_pickup_deadlines,
    # send_product_expired_notifications,  # DEPRECATED: Replaced by PRODUCT_EXPIRY_REACHED
)


@celery_app.task
def clean_expired_combos_and_lockers():
    """
    Celery task to clean up expired combos and their associated locker units.

    This task should be scheduled to run periodically (e.g., every hour).

    Returns:
        dict: Summary of cleanup operations
    """
    try:
        logging.info("Starting scheduled cleanup of expired combos and locker units")

        # Get database session
        db_gen = get_session()
        db: Session = next(db_gen)

        try:
            result = cleanup_expired_combos_and_lockers_service(db)
            logging.info(f"Cleanup task completed: {result}")
        finally:
            db.close()

    except Exception as e:
        logging.error(f"Error in cleanup task: {e}")


@celery_app.task
def clean_pickup_deadline_passed():
    """Task to send pickup deadline passed notification to buyer"""
    try:
        send_combo_passed_pickup_deadlines()
        logging.info(f"Successfully sent pickup deadline passed notification for combo")
    except Exception as e:
        logging.error(f"Error sending pickup deadline passed notification: {e}")


# DEPRECATED: Replaced by PRODUCT_EXPIRY_REACHED (trigger-based via apply_async eta)
# @celery_app.task
# def check_product_expired_date():
#     """Task to check for products with expired dates"""
#     try:
#         send_product_expired_notifications()
#         logging.info("Checked for products with expired dates successfully")
#     except Exception as e:
#         logging.error(f"Error checking for expired products: {e}")
