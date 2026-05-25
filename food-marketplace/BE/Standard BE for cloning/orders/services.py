"""
Order Business Logic Services
"""

from datetime import datetime, timedelta
from typing import List, Optional

from sqlmodel import Session, select

from apps.core.constants import (
    COMBO_STATUS_SELLING,
    COMBO_STATUS_SOLD,
    ORDER_STATUS_PENDING_PAYMENT,
    ORDER_STATUS_PICKED_UP,
    ORDER_STATUS_READY_FOR_PICKUP,
    ORDER_STATUS_REFUNDED,
    PAYMENT_CAPTURED,
    PICK_UP_DEADLINE,
    RESERVATION_STATUS_COMPLETED,
)
from apps.core.logging import logger
from apps.core.utils import get_current_time
from apps.integrations.aws.ses import send_email_via_ses
from apps.integrations.fincode.api_client import FincodeApiClient
from apps.integrations.mail.email_service import (
    get_template_path,
    render_email_template,
)
from apps.lockers.crud import get_locker_unit_by_id, update_locker_reservation
from apps.lockers.models.unit import LockerUnit
from apps.lockers.services import (
    _remove_galilei_code,
    generate_access_code_service,
)
from apps.products.crud import (
    get_combo_by_id,
    get_combo_locker_reservation,
    update_combo,
)
from apps.products.models.combos import Combo
from apps.purchase.schemas import PaymentRequest
from apps.purchase.services import payment_making_service
from apps.users.models import User

from .crud import (
    _delete_internal_order,
    create_order,
    get_order_by_combo,
    get_order_by_id,
    get_order_with_related_data,
    get_user_orders,
    update_order,
)
from .exceptions import (
    combo_not_available_for_purchase,
    fail_payment,
    order_already_completed,
    order_already_refunded,
    order_cannot_be_cancelled,
    order_not_found,
)
from .models.orders import Order
from .schemas import OrderCreate, OrderDetailRead, OrderRead
from .utils import (
    generate_order_number,
    generate_pickup_code,
    sales_duration_to_minutes,
)
from .validators import (
    validate_buy_combo,
    validate_combo_edited_at,
    validate_cooldown_buy_free_combo,
    validate_pickup_month,
)


def buy_combo_service(
    order_data: OrderCreate, user: User, db: Session, fincode_service: FincodeApiClient
) -> OrderRead:
    """Create a new order for a combo with card payment"""
    from apps.integrations.redis.lock import redis_lock

    # Use Redis distributed lock to prevent race condition with cancellation
    logger.info(f"Attempting to acquire lock for combo purchase: {order_data.combo_id}")
    with redis_lock(f"combo:{order_data.combo_id}", timeout=10, blocking_timeout=5):
        logger.info(f"Lock acquired for combo purchase: {order_data.combo_id}")

        validate_combo_edited_at(
            get_combo_by_id(db, order_data.combo_id), order_data.edited_at
        )

        # Get fresh combo data from DB after acquiring lock
        combo = validate_buy_combo(get_combo_by_id(db, order_data.combo_id))

        # Validate that combo hasn't been edited after client fetched it

        if (
            not (hasattr(order_data, "card_id") and getattr(order_data, "card_id"))
            and user.is_verification_qrcode
        ):
            validate_cooldown_buy_free_combo(user, db)

        existing_order = get_order_by_combo(db, order_data.combo_id)
        if existing_order:
            logger.warning(
                f"Combo {order_data.combo_id} already has an order: {existing_order.id}"
            )
            raise combo_not_available_for_purchase()

        order = _create_order_internal(
            combo,
            user,
            db,
            ORDER_STATUS_PENDING_PAYMENT,
            order_data.payment_method,
            order_data.notes,
        )

        if order.final_price == 0:
            return _handle_free_combo(order, combo, user, db)

        return _handle_paid_combo(
            order, combo, user, db, fincode_service, order_data.card_id
        )


def _generate_and_update_access_code(combo: Combo, order: Order, db: Session) -> None:
    """Generate new access code for user pickup and update reservation and order"""
    try:
        from apps.lockers.utils import generate_qr_code_url

        # Get the locker reservation for this combo
        reservation = get_combo_locker_reservation(db, combo.id)
        if not reservation:
            logger.warning(f"No reservation found for combo {combo.id}")
            return

        locker_unit = get_locker_unit_by_id(db, reservation.locker_unit_id)
        # Generate access code for pickup (put_in=False for BB prefix)
        new_access_code = generate_access_code_service(locker_unit, put_in=False)[2:]

        # Generate QR code and cache URL in order only (reservation is not updated)
        qr_url = generate_qr_code_url(new_access_code, str(reservation.id))
        order.qr_code_url = qr_url
        order.pickup_code = new_access_code

        logger.info(
            f"Generated new access code for combo {combo.id}, reservation {reservation.id}, order {order.id}"
        )

    except Exception as e:
        logger.error(f"Failed to generate access code for combo {combo.id}: {e}")
        # Don't raise exception to prevent order failure - this is not critical for order completion


def _handle_free_combo(
    order: Order, combo: Combo, user: User, db: Session
) -> OrderRead:
    """Handle free combo order completion"""
    order.status = ORDER_STATUS_READY_FOR_PICKUP
    order.payment_method = "free"
    order.completed_at = get_current_time()
    order = update_order(db, order)

    combo.status = COMBO_STATUS_SOLD
    combo.is_available = False
    update_combo(db, combo)

    # Generate new access code for user pickup
    _generate_and_update_access_code(combo, order, db)

    _send_order_notifications(combo, user, order)

    return OrderRead.model_validate(order, from_attributes=True)


def _handle_paid_combo(
    order: Order,
    combo: Combo,
    user: User,
    db: Session,
    fincode_service: FincodeApiClient,
    card_id: Optional[str],
) -> OrderRead:
    """Handle paid combo order with payment processing"""
    try:
        payment_request = PaymentRequest(
            user_id=user.id,
            shop_id=order.shop_id,
            order_number=order.order_number,
            amount=str(int(order.final_price)),
            card_id=card_id,
        )

        payment_response = payment_making_service(
            fincode_service=fincode_service,
            db=db,
            user=user,
            payment_request=payment_request,
        )

        if payment_response and isinstance(payment_response, dict):
            order.transaction_id = payment_response.get("access_id")

            if payment_response.get("status") == PAYMENT_CAPTURED:
                order.completed_at = get_current_time()
                order.status = ORDER_STATUS_READY_FOR_PICKUP

                combo.status = COMBO_STATUS_SOLD
                combo.is_available = False
                update_combo(db, combo)

                # Generate new access code for user pickup
                _generate_and_update_access_code(combo, order, db)

                _send_order_notifications(combo, user, order)
        else:
            # payment fail, dont create order
            # TODO: enhancement and refactor to dont need to delete order
            _delete_internal_order(db, order)
            raise fail_payment()

        order.updated_at = get_current_time()
        order = update_order(db, order)
        notify_order_event(db, order=order, combo=combo, event="paid")

        return OrderRead.model_validate(order, from_attributes=True)

    except Exception as e:
        _delete_internal_order(db, order)
        reservation = get_combo_locker_reservation(db, combo.id)
        locker_unit = get_locker_unit_by_id(db, reservation.locker_unit_id)
        _remove_galilei_code(locker_unit, put_in=False)
        raise e


def _send_order_notifications(combo: Combo, user: User, order: Order) -> None:
    """Send notifications for order completion"""
    from apps.integrations.celery.shops.tasks import send_user_buy_combo
    from apps.integrations.celery.users.tasks import send_pickup_deadline

    send_user_buy_combo.delay(combo_id=str(combo.id), shop_id=str(combo.shop_id))

    if order.pickup_deadline and order.status == ORDER_STATUS_READY_FOR_PICKUP:
        notification_time = order.pickup_deadline - timedelta(minutes=5)
        if notification_time > get_current_time():
            send_pickup_deadline.apply_async(
                args=[str(combo.id), str(user.id)], eta=notification_time
            )


def _calculate_free_pricing(combo: Combo, user: User) -> float:
    """
    Calculate final price for combo, applying free pricing logic for eligible users
    in the last 1/3 of sales time.

    Returns the final price (0.0 if free, combo.discount_price otherwise)
    """
    final_price = combo.discount_price or 0.0

    if not combo.is_free:
        return final_price

    try:
        user_has_mynaportal = bool(getattr(user, "my_portal", None) == "linked")
        user_has_verified_qr = bool(getattr(user, "is_verification_qrcode", False))

        if not (user_has_mynaportal or user_has_verified_qr):
            return final_price

        if not (combo.listing_end_date and combo.sales_duration):
            return final_price

        duration_minutes = sales_duration_to_minutes(combo.sales_duration)
        if not duration_minutes or duration_minutes <= 0:
            return final_price

        sale_end = combo.listing_end_date
        sale_start = sale_end - timedelta(minutes=duration_minutes)
        last_third_cutoff = sale_start + timedelta(
            minutes=max(1, duration_minutes * 2 // 3)
        )

        # If current time is AFTER the first 2/3 (i.e., in the last 1/3), make it free
        if get_current_time() >= last_third_cutoff:
            final_price = 0.0

    except Exception as e:
        # Fail-safe: do not break order creation if any unexpected data
        logger.warning(f"Free pricing logic skipped due to error: {e}")

    return final_price


def _get_locker_unit_for_combo(db: Session, combo: Combo) -> Optional[str]:
    """
    Get the locker unit ID from combo's reservation.

    Returns locker_unit_id if reservation exists, raises exception if combo has no reservation.
    """
    if not combo.id:
        return None

    from apps.products.crud import get_combo_locker_reservation

    reservation = get_combo_locker_reservation(db, combo.id)
    if not reservation:
        raise combo_not_available_for_purchase()

    return reservation.locker_unit_id


def _create_order_internal(
    combo: Combo,
    user: User,
    db: Session,
    status: str,
    payment_method: Optional[str] = None,
    notes: Optional[str] = None,
) -> Order:
    """
    Internal function to create an order.

    Validates combo availability, calculates pricing, reserves locker unit,
    and creates the order record.
    """
    if combo.status != COMBO_STATUS_SELLING or not combo.is_available:
        raise combo_not_available_for_purchase()

    # Calculate final price (may be free for eligible users)
    final_price = _calculate_free_pricing(combo, user)

    # Create pickup code and deadline
    pickup_code = generate_pickup_code()
    pickup_deadline = combo.pickup_deadline or (
        get_current_time() + timedelta(minutes=PICK_UP_DEADLINE)
    )

    # Get locker unit ID from combo's reservation
    locker_unit_id = _get_locker_unit_for_combo(db, combo)

    # Create order
    order = Order(
        user_id=user.id,
        combo_id=combo.id,
        shop_id=combo.shop_id,
        locker_unit_id=locker_unit_id,
        order_number=generate_order_number(),
        status=status,
        original_price=combo.original_price or 0.0,
        discount_percentage=combo.discount_percentage,
        final_price=final_price,
        pickup_code=pickup_code,
        pickup_deadline=pickup_deadline,
        payment_method=payment_method or ("free" if final_price == 0 else "card"),
        notes=notes,
        completed_at=None,
    )
    order = create_order(db, order)
    return order


def handle_payment_webhook_service(
    order_id: str, payment_status: str, transaction_id: str, db: Session
) -> Optional[OrderRead]:
    """Handle payment webhook from Fincode to update order status"""

    order = get_order_by_id(db, order_id)
    if not order:
        return None

    # Only update orders that are pending payment
    if order.status != ORDER_STATUS_PENDING_PAYMENT:
        return None

    # Update order based on payment status
    # if payment_status == PAYMENT_CAPTURED:
    #    order.status = ORDER_STATUS_READY_FOR_PICKUP
    #    order.transaction_id = transaction_id
    #    order.completed_at = get_current_time()

    #    # Mark combo as sold
    #    combo = get_combo_by_id(db, order.combo_id)
    #    if combo:
    #        combo.status = COMBO_STATUS_SOLD
    #        update_combo(db, combo)

    order.updated_at = get_current_time()
    order = update_order(db, order)

    return OrderRead.model_validate(order, from_attributes=True)


def get_order_service(order_id: str, user: User, db: Session) -> OrderRead:
    """Get order details for a user"""
    order = get_order_by_id(db, order_id)
    if not order:
        raise order_not_found()

    # Ensure user can only see their own orders (unless admin)
    if user.role != "admin" and order.user_id != user.id:
        raise order_not_found()

    return OrderRead.model_validate(order, from_attributes=True)


def get_order_detail_service(order_id: str, user: User, db: Session) -> OrderDetailRead:
    """Get enhanced order details with related objects for a user"""
    order_data = get_order_with_related_data(db, order_id)
    if not order_data:
        raise order_not_found()

    order = order_data["order"]

    # Ensure user can only see their own orders (unless admin)
    if user.role != "admin" and order.user_id != user.id:
        raise order_not_found()

    # Build the response
    order_dict = order.__dict__.copy()
    order_dict.pop("_sa_instance_state", None)
    # Remove the foreign key fields since they're now in the objects
    order_dict.pop("combo_id", None)
    order_dict.pop("shop_id", None)

    # Add related data
    order_dict["shop"] = order_data["shop"]
    order_dict["combo"] = order_data["combo"]
    order_dict["locker"] = order_data["locker"]

    order_dict["qr_code_url"] = order.qr_code_url
    order_dict["is_qr_active"] = order.status == ORDER_STATUS_READY_FOR_PICKUP
    order_dict["is_review"] = bool(getattr(order, "is_review", False))

    return OrderDetailRead.model_validate(order_dict)


def get_user_orders_service(
    user: User,
    db: Session,
    limit: int = 20,
    offset: int = 0,
    status: Optional[str] = None,
    pickup_month: Optional[str] = None,
) -> tuple[list[OrderRead], int]:

    validate_pickup_month(pickup_month)
    # Compute start/end time for pickup month in service layer
    pickup_start = pickup_end = None
    if pickup_month:
        # validate already done above; safe to parse
        month_start = datetime.strptime(pickup_month + "-01", "%Y-%m-%d")
        if month_start.month == 12:
            pickup_end = month_start.replace(year=month_start.year + 1, month=1)
        else:
            pickup_end = month_start.replace(month=month_start.month + 1)
        pickup_start = month_start

    orders, total = get_user_orders(
        db, user.id, limit, offset, status, pickup_start, pickup_end
    )

    order_reads = [OrderRead.build(order) for order in orders]

    return order_reads, total


def confirm_pickup_service(order_id: str, pickup_code: str, db: Session) -> OrderRead:
    """Confirm order pickup with pickup code"""
    order = get_order_by_id(db, order_id)
    if not order:
        raise order_not_found()

    combo = get_combo_by_id(db, order.combo_id)
    if not combo:
        raise combo_not_available_for_purchase()

    # Validate pickup code
    if order.pickup_code != pickup_code:
        from .exceptions import invalid_pickup_code

        raise invalid_pickup_code()

    # Check if already picked up
    if order.status == ORDER_STATUS_PICKED_UP:
        raise order_already_completed()

    # Update order status
    order.status = ORDER_STATUS_PICKED_UP
    order.picked_up_at = get_current_time()
    order.updated_at = get_current_time()

    # The locker unit status will be automatically updated to "available"
    # by the after_update event handler in the Order model
    # The user's food loss reduction stats will also be automatically synced to Firebase
    order = update_order(db, order)

    # Update locker reservation status to COMPLETED when order is picked up
    reservation = get_combo_locker_reservation(db, combo.id)
    if reservation:
        update_locker_reservation(
            db,
            reservation.id,
            {
                "status": RESERVATION_STATUS_COMPLETED,
                "item_collected_at": get_current_time(),
            },
        )
        logger.info(
            f"Updated reservation {reservation.id} status to COMPLETED after order {order.id} pickup"
        )

    if order.locker_unit_id:
        unit = db.get(LockerUnit, order.locker_unit_id)
        if unit:
            from apps.lockers.services import _remove_galilei_code
            _remove_galilei_code(unit, put_in=False)

    # Prepare data for notification/email
    combo.name if combo else ""
    combo.product_number if combo else ""
    pickup_datetime = (
        order.picked_up_at.strftime("%Y-%m-%d %H:%M:%S") if order.picked_up_at else ""
    )
    notify_order_event(db, order=order, combo=combo, event=ORDER_STATUS_PICKED_UP)
    return OrderRead.model_validate(order, from_attributes=True)


def _collect_recipients_for_order(
    db: Session, shop_id: Optional[str], locker_unit_id: Optional[str]
) -> List[str]:
    recipients: List[str] = []

    # Shop owner and staff
    if shop_id:
        from apps.shops.models.shops import Shop
        from apps.users.models.users import User as AppUser

        shop = db.get(Shop, shop_id)
        if shop and shop.owner and shop.owner.email:
            recipients.append(shop.owner.email)

        staff_users = db.exec(
            select(AppUser).where(AppUser.shop_id == shop_id, AppUser.is_active == True)
        ).all()
        for su in staff_users:
            if su.email:
                recipients.append(su.email)

    # Locker owner
    if locker_unit_id:
        unit = db.get(LockerUnit, locker_unit_id)
        if unit and unit.location and unit.location.owner and unit.location.owner.email:
            recipients.append(unit.location.owner.email)

    # Deduplicate and filter empties
    return list({r for r in recipients if r})


def notify_order_event(db: Session, *, order: Order, combo, event: str) -> None:
    """Send notification email for order events. event ∈ {"paid", "picked_up"}."""
    try:
        # Common fields
        locker_name = None
        if order.locker_unit_id:
            unit = db.get(LockerUnit, order.locker_unit_id)
            if unit and unit.location:
                locker_name = unit.location.name

        product_name = combo.name if combo else ""
        product_code = combo.product_number if combo else ""

        if event == "paid":
            title = "【wakeatte】商品販売のご報告"
            template = "email_order_paid.ja.html"
            dt_value = (
                (order.completed_at + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
                if order.completed_at
                else ""
            )
            context = {
                "title_email": title,
                "locker_name": locker_name or "",
                "product_name": product_name,
                "datetime": dt_value,
                "product_code": product_code,
            }
        elif event == ORDER_STATUS_PICKED_UP:
            title = "【wakeatte】商品受け取り完了のご連絡"
            template = "email_order_picked_up.ja.html"
            dt_value = (
                (order.picked_up_at + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
                if order.picked_up_at
                else ""
            )
            context = {
                "title_email": title,
                "locker_name": locker_name or "",
                "product_name": product_name,
                "datetime": dt_value,
                "product_code": product_code,
            }
        else:
            return

        template_path = get_template_path(template)
        html = render_email_template(str(template_path), context)
        if not html:
            return

        shop_id = combo.shop_id if combo else None
        recipients = _collect_recipients_for_order(db, shop_id, order.locker_unit_id)
        for email in recipients:
            send_email_via_ses(
                recipient_email=email,
                subject=title,
                html_content=html,
            )
    except Exception as e:
        logger.error(f"notify_order_event error: {e}")


def admin_refund_order_service(
    order_id: str,
    db: Session,
    fincode_service: FincodeApiClient,
) -> OrderRead:
    """
    Admin-only: cancel (full refund) payment via Fincode for operational issues / customer claims.
    Sets order.status = REFUNDED. Combo status remains SOLD (item already picked up).
    """
    from apps.purchase.services import payment_cancel_service

    order = get_order_by_id(db, order_id)
    if not order:
        raise order_not_found()

    refundable_statuses = [ORDER_STATUS_PICKED_UP]
    if order.status == ORDER_STATUS_REFUNDED:
        raise order_already_refunded()
    if order.status not in refundable_statuses:
        raise order_cannot_be_cancelled()

    payment_cancel_service(
        fincode_service=fincode_service,
        db=db,
        order_id=order_id,
    )

    order.status = ORDER_STATUS_REFUNDED
    order.updated_at = get_current_time()
    order = update_order(db, order)

    return OrderRead.model_validate(order, from_attributes=True)

