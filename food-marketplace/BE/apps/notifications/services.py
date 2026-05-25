import logging
from typing import List
from sqlmodel import Session

from apps.notifications.models import Notification
from apps.devices.crud import get_tokens_by_user, get_all_tokens_for_users
from apps.integrations.firebase_client import firebase_service

logger = logging.getLogger(__name__)


def _save_notification(db: Session, user_id: str, title: str, body: str,
                        ntype: str, ref_id: str = None) -> Notification:
    notif = Notification(
        user_id=user_id, title=title, body=body,
        notification_type=ntype, reference_id=ref_id,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif


def _push_to_user(db: Session, user_id: str, title: str, body: str, data: dict = {}):
    tokens = get_tokens_by_user(db, user_id)
    if tokens:
        firebase_service.send_push_multicast(tokens, title, body, data)


def notify_combo_available(db: Session, combo_id: str, shop_name: str, locker_name: str):
    from apps.favorites.crud import get_user_ids_following_shop, get_user_ids_following_locker
    from apps.combos.crud import get_combo_by_id
    combo = get_combo_by_id(db, combo_id)
    if not combo:
        return

    title = f"Новый набор — {shop_name}"
    body = f"В ячейке {locker_name} появился новый набор. Успейте купить!"

    follower_ids = set(get_user_ids_following_shop(db, combo.shop_id))
    follower_ids.update(get_user_ids_following_locker(db, combo.locker_location_id))

    for uid in follower_ids:
        _save_notification(db, uid, title, body, "combo_available", combo_id)

    tokens = get_all_tokens_for_users(db, list(follower_ids))
    if tokens:
        firebase_service.send_push_multicast(tokens, title, body, {"combo_id": combo_id})


def notify_order_paid(db: Session, order_id: str, customer_id: str, shop_owner_id: str):
    from apps.orders.crud import get_order_by_id
    order = get_order_by_id(db, order_id)
    if not order:
        return

    # Notify customer
    title = "Оплата прошла успешно!"
    body = f"Код для открытия ячейки: {order.access_code}"
    _save_notification(db, customer_id, title, body, "order_paid", order_id)
    _push_to_user(db, customer_id, title, body, {"order_id": order_id})

    # Notify shop owner
    shop_title = "Новая покупка!"
    shop_body = f"Ваш набор был куплен. Сумма: {order.amount} ₽"
    _save_notification(db, shop_owner_id, shop_title, shop_body, "order_paid", order_id)
    _push_to_user(db, shop_owner_id, shop_title, shop_body, {"order_id": order_id})
