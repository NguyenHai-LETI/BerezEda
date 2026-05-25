import logging
from datetime import datetime

from sqlmodel import Session, select

from apps.core.constants import (
    COMBO_STATUS_SOLD,
    ORDER_STATUS_PICKED_UP,
    ORDER_STATUS_READY_FOR_PICKUP,
)
from apps.core.database import engine
from apps.core.utils import get_current_time
from apps.lockers.services import _remove_galilei_code
from apps.notifications.constants import NotificationType
from apps.notifications.services.send_noti import send_push_notification
from apps.notifications.templates import NOTIFICATION_TEMPLATES
from apps.notifications.utils import complete_reservation_and_release_locker
from apps.products.models import Combo
from apps.shops.models.shops import Shop
from apps.users.models import User


def send_combo_pickup_deadline_approaching_notification(combo_id: str, user_id: str):
    """Buyer notification: 5 minutes before pickup deadline"""
    from apps.lockers.models.reservation import LockerReservation
    from apps.orders.models import Order

    with Session(engine) as session:
        combo = session.exec(
            select(Combo)
            .where(Combo.id == combo_id)
            .where(Combo.status == COMBO_STATUS_SOLD)
        ).first()
        user = session.exec(select(User).where(User.id == user_id)).first()

        if not combo or not user:
            return

        # Get order information - query without status filter to get latest status
        order = session.exec(
            select(Order)
            .where(Order.combo_id == combo_id)
            .where(Order.user_id == user_id)
        ).first()

        # Check if order exists and is still in READY_FOR_PICKUP status
        if not order or order.status != ORDER_STATUS_READY_FOR_PICKUP:
            logging.info(
                f"Skipping pickup deadline notification for combo {combo_id} - "
                f"order status is {order.status if order else 'not found'}"
            )
            return

        # Get locker information
        reservation = session.exec(
            select(LockerReservation).where(LockerReservation.combo_id == combo_id)
        ).first()

        locker_name = ""
        if reservation and reservation.unit and reservation.unit.location:
            locker_name = reservation.unit.location.name or ""

        # Check Galilei to see if user already picked up the item
        if order.locker_unit_id and order.pickup_code and order.completed_at:
            from datetime import timedelta

            from apps.lockers.models.unit import LockerUnit
            from apps.lockers.services import verify_galilei_door_activity

            locker_unit = session.get(LockerUnit, order.locker_unit_id)
            if locker_unit:
                from_date_jst = (
                    order.completed_at + timedelta(hours=9)
                ).strftime("%Y%m%d%H%M%S")
                to_date_jst = (
                    get_current_time() + timedelta(hours=9)
                ).strftime("%Y%m%d%H%M%S")

                already_picked_up, _ = verify_galilei_door_activity(
                    locker_unit=locker_unit,
                    access_code=order.pickup_code,
                    from_date=from_date_jst,
                    to_date=to_date_jst,
                    put_in=False,
                )

                if already_picked_up:
                    logging.info(
                        f"Skipping pickup deadline notification for combo {combo_id} - "
                        f"Galilei confirms user already picked up the item"
                    )
                    return

        # Get shop information
        shop = session.exec(select(Shop).where(Shop.id == combo.shop_id)).first()

        template = NOTIFICATION_TEMPLATES[
            NotificationType.COMBO_PICKUP_DEADLINE_APPROACHING
        ]

        extra_data = {
            "store_name": shop.name if shop else "",
            "phone_number": shop.phone if shop else "",
            "shop_id": combo.shop_id if combo.shop_id else "",
            "locker_name": locker_name,
            "order_id": order.id if order else "",
            "order_pickup_code": order.pickup_code if order else "",
        }

        send_push_notification(
            session,
            user,
            template,
            combo,
            NotificationType.COMBO_PICKUP_DEADLINE_APPROACHING,
            extra_data=extra_data,
        )


def _expire_and_cancel_order_and_release_resources(
    session: Session, user: User, order, combo
) -> None:
    """
    Helper function to expire an order and release associated resources.

    This handles:
    - Attempting to cancel order if possible (with payment refund)
    - If cancellation not possible, updating order status to expired
    - Completing reservations and releasing locker units
    - Syncing to Firebase
    """

    # fincode_service = None

    # try:
    # Try to cancel order first (this handles payment refund)
    # from apps.integrations.fincode.api_client import FincodeApiClient

    # fincode_service = FincodeApiClient()

    # cancel_result = cancel_order_service(
    #     order.id, user, session, fincode_service, auto=True
    # )

    # Refresh order to get latest status from database
    # session.refresh(order)

    # except Exception as e:
    #     # If cancellation fails (e.g., already picked up), rollback and proceed to expiration
    #     session.rollback()
    #     logging.info(
    #         f"Could not cancel order {order.id}: {str(e)}. Proceeding to expire order."
    #     )

    # finally:
    # Always close fincode service if it was created
    # if fincode_service:
    # fincode_service.close()

    # Check if order is still not in final state - if so, expire it
    if order.status == ORDER_STATUS_READY_FOR_PICKUP:
        try:
            # Update order status to expired
            order.status = ORDER_STATUS_PICKED_UP  # change order status from EXPIRED to PICKED_UP since logic change
            order.updated_at = get_current_time()
            order.completed_at = get_current_time()
            session.add(order)
            session.commit()

            # Complete reservation and release locker unit
            complete_reservation_and_release_locker(session, combo.id)
            logging.info(f"Order {order.id} expired successfully")

        except Exception as e:
            logging.error(
                f"Failed to expire order {order.id} or release locker for combo {combo.id}: {str(e)}"
            )
            session.rollback()


def send_combo_passed_pickup_deadlines():
    """
    Scheduled task to check and handle combos with passed pickup deadlines.

    For each expired order:
    - Send notification to buyer
    - Regenerate BB code for locker unit
    - Mark order as expired
    - Release locker unit and complete reservation
    """
    from apps.core.constants import ORDER_STATUS_READY_FOR_PICKUP
    from apps.orders.models import Order

    with Session(engine) as session:
        current_time = get_current_time()

        # Query orders that are READY_FOR_PICKUP with passed deadlines
        orders_to_expire = session.exec(
            select(Order)
            .where(Order.status == ORDER_STATUS_READY_FOR_PICKUP)
            .where(Order.pickup_deadline != None)  # type: ignore
            .where(Order.pickup_deadline < current_time)  # type: ignore
        ).all()

        for order in orders_to_expire:
            # Get combo and user
            combo = session.exec(
                select(Combo).where(Combo.id == order.combo_id)
            ).first()
            user = session.exec(select(User).where(User.id == order.user_id)).first()

            # Skip if combo or user not found
            if not combo or not user:
                continue

            # Get locker name for notification
            locker_name = "N/A"
            locker_unit = None
            if order.locker_unit_id:
                from apps.lockers.models.unit import LockerUnit

                locker_unit = session.get(LockerUnit, order.locker_unit_id)
                if locker_unit and locker_unit.location:
                    locker_name = locker_unit.location.name or "N/A"

            # Check Galilei to see if user already picked up the item
            if locker_unit and order.pickup_code and order.completed_at:
                from datetime import timedelta

                from apps.lockers.services import verify_galilei_door_activity

                from_date_jst = (
                    order.completed_at + timedelta(hours=9)
                ).strftime("%Y%m%d%H%M%S")
                to_date_jst = (
                    current_time + timedelta(hours=9)
                ).strftime("%Y%m%d%H%M%S")

                already_picked_up, _ = verify_galilei_door_activity(
                    locker_unit=locker_unit,
                    access_code=order.pickup_code,
                    from_date=from_date_jst,
                    to_date=to_date_jst,
                    put_in=False,
                )

                if already_picked_up:
                    logging.info(
                        f"Skipping deadline passed notification for order {order.id} - "
                        f"Galilei confirms user already picked up the item"
                    )
                    # Still remove BB code and expire order, but skip notification
                    if locker_unit is not None:
                        _remove_galilei_code(locker_unit, put_in=False)
                    _expire_and_cancel_order_and_release_resources(session, user, order, combo)
                    continue

            # Get shop information
            shop = session.exec(select(Shop).where(Shop.id == combo.shop_id)).first()

            # Send notification to user
            template = NOTIFICATION_TEMPLATES[
                NotificationType.COMBO_PICKUP_DEADLINE_PASSED
            ]

            extra_data = {
                "locker_name": locker_name,
                "store_name": shop.name if shop else "",
                "phone_number": shop.phone if shop else "",
                "shop_id": combo.shop_id if combo.shop_id else "",
            }

            send_push_notification(
                session,
                user,
                template,
                combo,
                NotificationType.COMBO_PICKUP_DEADLINE_PASSED,
                extra_data=extra_data,
            )

            # remove BB code when order expired
            if locker_unit is not None:
                _remove_galilei_code(locker_unit, put_in=False)

            # Expire order and release resources
            _expire_and_cancel_order_and_release_resources(session, user, order, combo)


def handle_new_combo_published(combo_id: str, shop_id: str):
    """Called when store publishes new combo - notify favorite store followers"""
    with Session(engine) as session:
        combo = session.exec(select(Combo).where(Combo.id == combo_id)).first()
        shop = session.exec(select(Shop).where(Shop.id == shop_id)).first()

        if not combo or not shop:
            return

        # Get all users who have this shop as favorite
        users = shop.get_all_users_favoriting_shop()  # type: ignore

        template = NOTIFICATION_TEMPLATES[
            NotificationType.NEW_COMBO_FROM_FAVORITE_STORE
        ]

        # Add store_name to extra_data
        extra_data = {"store_name": shop.name or "Unknown Store"}

        for user in users:
            send_push_notification(
                session,
                user,
                template,
                combo,
                NotificationType.NEW_COMBO_FROM_FAVORITE_STORE,
                extra_data=extra_data,
            )


def send_order_canceled_notification(combo_id: str, user_id: str):
    """Buyer notification: When buyer cancels order (refund notification)"""
    with Session(engine) as session:
        combo = session.exec(select(Combo).where(Combo.id == combo_id)).first()
        user = session.exec(select(User).where(User.id == user_id)).first()

        if not combo or not user:
            return

        template = NOTIFICATION_TEMPLATES[NotificationType.ORDER_CANCELED]
        send_push_notification(
            session, user, template, combo, NotificationType.ORDER_CANCELED
        )


def send_product_expired_notifications():
    """
    Scheduled task to notify users 30 minutes before product expiration.

    For each combo that has been purchased (SOLD status):
    - Check all product_masters in the combo
    - For each product with expiry_dates, check if any expiry is within 30 minutes
    - Send notification to the buyer once per combo
    """
    from datetime import timedelta

    from apps.core.constants import ORDER_STATUS_PICKED_UP
    from apps.orders.models import Order

    with Session(engine) as session:
        current_time = get_current_time()
        expiry_threshold = current_time + timedelta(minutes=3)

        # Get all orders that have been picked up
        picked_up_orders = session.exec(
            select(Order).where(Order.status == ORDER_STATUS_PICKED_UP)
        ).all()

        for order in picked_up_orders:
            # Get the combo for this order
            combo = session.exec(
                select(Combo).where(Combo.id == order.combo_id)
            ).first()

            if not combo:
                continue

            # Check if any product in this combo is expiring soon
            should_notify = False

            for combo_product in combo.combo_products:
                if not combo_product.expiry_dates:
                    continue

                # Check each expiry date in the product
                for expiry_date_str in combo_product.expiry_dates:
                    try:
                        # Parse ISO format datetime string (e.g., "2025-11-21T13:30:00")
                        if isinstance(expiry_date_str, str):
                            expiry_date = datetime.fromisoformat(expiry_date_str)
                        else:
                            expiry_date = expiry_date_str

                        # Check if expiry is within the next 30 minutes
                        if current_time <= expiry_date <= expiry_threshold:
                            should_notify = True
                            break
                    except (ValueError, TypeError) as e:
                        logging.warning(
                            f"Failed to parse expiry date '{expiry_date_str}' for combo {combo.id}: {e}"
                        )
                        continue

                if should_notify:
                    break

            # Send notification to the buyer if product is expiring soon
            if should_notify:
                user = combo.bought_by()
                if user:
                    template = NOTIFICATION_TEMPLATES[NotificationType.PRODUCT_EXPIRED]
                    send_push_notification(
                        session, user, template, combo, NotificationType.PRODUCT_EXPIRED
                    )


def send_product_expiry_reached_notification(
    combo_id: str, user_id: str, combo_product_id: str
):
    """
    Send notification to buyer when a specific combo_product's expiry date is reached.

    Triggered by Celery task scheduled at exact expiry time (via apply_async with eta).
    Each combo_product gets its own notification since they can have different expiry dates.
    Asks the buyer whether they've consumed the product or will dispose of the remainder.
    """
    from apps.notifications.models import Notification
    from apps.orders.models import Order

    with Session(engine) as session:
        combo = session.exec(
            select(Combo)
            .where(Combo.id == combo_id)
            .where(Combo.status == COMBO_STATUS_SOLD)
        ).first()
        user = session.exec(select(User).where(User.id == user_id)).first()

        if not combo or not user:
            return

        # Get order for this combo+user and verify status
        order = session.exec(
            select(Order)
            .where(Order.combo_id == combo_id)
            .where(Order.user_id == user_id)
            .where(Order.status == ORDER_STATUS_PICKED_UP)
        ).first()

        if not order:
            return

        # Safety duplicate check: skip if notification already sent for this combo_product
        existing_noti = session.exec(
            select(Notification)
            .where(
                Notification.notification_type
                == NotificationType.PRODUCT_EXPIRY_REACHED.value
            )
            .where(Notification.target_id == combo_product_id)
        ).first()

        if existing_noti:
            logging.info(
                f"Skipping duplicate PRODUCT_EXPIRY_REACHED notification "
                f"for combo_product {combo_product_id}"
            )
            return

        # Get product_master name for notification content
        from apps.products.models.combo_products import ComboProduct

        combo_product = session.get(ComboProduct, combo_product_id)
        product_master_name = ""
        if combo_product and combo_product.product_master:
            product_master_name = combo_product.product_master.name or ""

        template = NOTIFICATION_TEMPLATES[NotificationType.PRODUCT_EXPIRY_REACHED]
        extra_data = {
            "combo_product_id": combo_product_id,
            "product_master_name": product_master_name,
        }
        send_push_notification(
            session,
            user,
            template,
            combo,
            NotificationType.PRODUCT_EXPIRY_REACHED,
            extra_data=extra_data,
        )
