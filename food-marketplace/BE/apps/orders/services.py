from typing import Optional
from datetime import timedelta
from sqlmodel import Session

from apps.core.utils import utcnow

from apps.orders import crud
from apps.orders.exceptions import (
    order_not_found, order_access_denied, order_not_paid,
    order_pickup_expired, combo_already_sold, wrong_access_code,
)
from apps.orders.models import Order
from apps.combos.services import get_combo_or_404
from apps.combos.crud import mark_combo_sold
from apps.combos.exceptions import combo_not_available
from apps.lockers.services import mark_unit_available
from apps.core.config import COMBO_PICKUP_DEADLINE_MINUTES
from apps.integrations.firebase_client import firebase_service


def get_order_or_404(db: Session, order_id: str, customer_id: Optional[str] = None) -> Order:
    from typing import Optional
    order = crud.get_order_by_id(db, order_id)
    if not order:
        raise order_not_found()
    if customer_id and order.customer_id != customer_id:
        raise order_access_denied()
    return order


def create_order(db: Session, customer_id: str, combo_id: str) -> Order:
    combo = get_combo_or_404(db, combo_id)
    if combo.status != "available":
        raise combo_not_available()

    # Check if combo still valid
    if combo.sale_end_time and combo.sale_end_time < utcnow():
        raise combo_already_sold()

    order_data = {
        "customer_id": customer_id,
        "combo_id": combo.id,
        "shop_id": combo.shop_id,
        "locker_unit_id": combo.locker_unit_id,
        "locker_location_id": combo.locker_location_id,
        "status": "pending",
        "amount": combo.sale_price,
        "original_amount": combo.original_price,
        "discount_rate": combo.discount_rate,
        "access_code": combo.access_code,
        "fincode_order_id": combo_id,
    }
    return crud.create_order(db, order_data)


def mark_order_paid(db: Session, order: Order) -> Order:
    import httpx
    from apps.core.config import LOCKER_SIM_URL
    from apps.scheduler.scheduler import schedule_order_expiry

    deadline = utcnow() + timedelta(minutes=COMBO_PICKUP_DEADLINE_MINUTES)
    order = crud.update_order(db, order, {
        "status": "paid",
        "paid_at": utcnow(),
        "pickup_deadline": deadline,
    })
    from apps.combos.crud import get_combo_by_id, mark_combo_sold
    combo = get_combo_by_id(db, order.combo_id)
    shop_owner_id = None
    if combo:
        mark_combo_sold(db, combo)
        # Remove combo from Firestore — no longer available for purchase
        firebase_service.delete_combo(str(combo.id))
        # Get shop owner for notification
        from apps.shops.crud import get_shop_by_id
        shop = get_shop_by_id(db, combo.shop_id)
        if shop:
            shop_owner_id = shop.owner_id

    # Register BB pickup code in System 2 and store it as order.access_code
    try:
        res = httpx.post(
            f"{LOCKER_SIM_URL}/locker-codes/register-pickup",
            json={
                "locker_unit_id": order.locker_unit_id,
                "location_id": order.locker_location_id,
                "combo_id": order.combo_id,
                "order_id": order.id,
                "expires_at": deadline.isoformat(),
            },
            timeout=5.0,
        )
        if res.status_code == 200:
            bb_code = res.json().get("data", {}).get("code")
            if bb_code:
                order = crud.update_order(db, order, {"access_code": bb_code})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(
            "BB code registration failed for order %s: %s", order.id, e
        )

    schedule_order_expiry(order.id, deadline)
    # Send notifications (best-effort, don't fail if notification errors)
    try:
        from apps.notifications.services import notify_order_paid
        notify_order_paid(db, order.id, order.customer_id, shop_owner_id or order.shop_id)
    except Exception:
        pass
    return order


def pickup_order(db: Session, order_id: str, customer_id: str, access_code: str) -> Order:
    order = get_order_or_404(db, order_id, customer_id)
    if order.status != "paid":
        raise order_not_paid()
    if order.pickup_deadline and order.pickup_deadline < utcnow():
        raise order_pickup_expired()
    if order.access_code != access_code:
        raise wrong_access_code()
    from apps.scheduler.scheduler import cancel_order_expiry
    cancel_order_expiry(order.id)
    mark_unit_available(db, order.locker_unit_id)
    # Safety: ensure combo is removed from Firestore (should already be gone after payment)
    firebase_service.delete_combo(str(order.combo_id))
    return crud.update_order(db, order, {"status": "completed", "completed_at": utcnow()})


def pickup_by_code(db: Session, customer_id: str, access_code: str):
    """Find order by access_code and mark as completed. Used by locker simulator."""
    order = crud.find_order_by_access_code(db, access_code, customer_id)
    if not order:
        raise wrong_access_code()
    if order.pickup_deadline and order.pickup_deadline < utcnow():
        raise order_pickup_expired()
    from apps.scheduler.scheduler import cancel_order_expiry
    cancel_order_expiry(order.id)
    mark_unit_available(db, order.locker_unit_id)
    # Safety: ensure combo is removed from Firestore (should already be gone after payment)
    firebase_service.delete_combo(str(order.combo_id))
    return crud.update_order(db, order, {"status": "completed", "completed_at": utcnow()})
