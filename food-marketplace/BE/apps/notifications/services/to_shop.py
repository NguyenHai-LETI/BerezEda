from datetime import datetime
from typing import Optional

from sqlmodel import Session, col, select
from apps.core.utils import utcnow

from apps.core.constants import (
    COMBO_STATUS_EXPIRED,
    COMBO_STATUS_SELLING,
    RESERVATION_STATUS_PENDING,
)
from apps.core.database import engine
from apps.notifications.constants import NotificationType
from apps.notifications.services.send_noti import send_push_notification
from apps.notifications.templates import NOTIFICATION_TEMPLATES
from apps.notifications.utils import complete_reservation_and_release_locker
from apps.products.models import Combo
from apps.reviews.models.reviews import Review
from apps.shops.models.shops import Shop
from apps.users.models import User


def send_combo_cancelled(combo_id: str, shop_id: str):
    """Store notification: When combo reservation is cancelled"""
    with Session(engine) as session:
        combo = session.exec(select(Combo).where(Combo.id == combo_id)).first()
        shop = session.exec(select(Shop).where(Shop.id == shop_id)).first()

        if not combo or not shop:
            return

        users = shop.get_all_shop_users()
        template = NOTIFICATION_TEMPLATES[NotificationType.USER_CANCELLED_COMBO]

        for user in users:
            send_push_notification(
                session, user, template, combo, NotificationType.USER_CANCELLED_COMBO
            )


def send_combo_expired_notification(combo: Combo, user: User):
    """Store notification: When combo expiration date has passed"""
    with Session(engine) as session:
        if not combo or not user:
            return
        template = NOTIFICATION_TEMPLATES[NotificationType.COMBO_EXPIRED_SALES]
        send_push_notification(
            session, user, template, combo, NotificationType.COMBO_EXPIRED_SALES
        )


def send_combo_reserved_notification(combo_id: str, shop_id: str):
    """Store notification: When buyer completes combo reservation"""
    with Session(engine) as session:
        combo = session.exec(select(Combo).where(Combo.id == combo_id)).first()
        shop = session.exec(select(Shop).where(Shop.id == shop_id)).first()

        if not combo or not shop:
            return
        users = shop.get_all_shop_users()
        for user in users:
            template = NOTIFICATION_TEMPLATES[NotificationType.USER_BUY_COMBO]
            send_push_notification(
                session, user, template, combo, NotificationType.USER_BUY_COMBO
            )


def send_combo_pickup_completed_notification(combo_id: str, shop_id: str):
    """Store notification: When buyer successfully picks up combo"""
    with Session(engine) as session:
        combo = session.exec(select(Combo).where(Combo.id == combo_id)).first()
        shop = session.exec(select(Shop).where(Shop.id == shop_id)).first()

        if not combo or not shop:
            return

        users = shop.get_all_shop_users()
        for user in users:
            template = NOTIFICATION_TEMPLATES[NotificationType.COMBO_PICKUP_COMPLETED]
            send_push_notification(
                session, user, template, combo, NotificationType.COMBO_PICKUP_COMPLETED
            )


def send_new_review_received_notification(
    combo_id: str, shop_owner_id: str, new_review_id: str
):
    """Store notification: When buyer posts combo review"""
    with Session(engine) as session:
        combo = session.exec(select(Combo).where(Combo.id == combo_id)).first()
        user = session.exec(select(User).where(User.id == shop_owner_id)).first()
        review = session.exec(select(Review).where(Review.id == new_review_id)).first()

        if not combo or not user or not review:
            return

        template = NOTIFICATION_TEMPLATES[NotificationType.NEW_REVIEW_RECEIVED]
        send_push_notification(
            session,
            user,
            template,
            combo,
            NotificationType.NEW_REVIEW_RECEIVED,
            extra_data={
                "review": review,
                "review_content": review.comment or "Без комментария",
            },
        )


def send_combo_placement_deadline_approaching_notification(
    reservation_id: str, shop_owner_id: str
):
    """Store notification: 5 minutes before combo placement deadline"""
    with Session(engine) as session:
        from apps.lockers.models.reservation import LockerReservation

        reservation = session.exec(
            select(LockerReservation).where(
                LockerReservation.id == reservation_id,
                LockerReservation.status == RESERVATION_STATUS_PENDING,
            )
        ).first()
        user = session.exec(select(User).where(User.id == shop_owner_id)).first()

        if not reservation or not user:
            return

        combo = reservation.combo
        unit = reservation.unit
        location = unit.location if unit else None

        if combo and user:
            template = NOTIFICATION_TEMPLATES[
                NotificationType.COMBO_PLACEMENT_DEADLINE_APPROACHING
            ]

            extra_data = {
                "locker_name": location.name if location else "Unknown Locker",
                "unit_number": unit.unit_number if unit else "Unknown",
            }

            send_push_notification(
                session,
                user,
                template,
                combo,
                NotificationType.COMBO_PLACEMENT_DEADLINE_APPROACHING,
                extra_data=extra_data,
            )


def cleanup_expired_combos_and_lockers_service(
    db: Session, current_time: Optional[datetime] = None
):
    """
    Cleanup expired combos and release associated locker units.

    This scheduled task:
    - Marks expired combos (SELLING) as EXPIRED
    - Notifies shop owners/staff
    - Releases locker units
    - Completes reservations
    - Syncs changes to Firebase
    - Deletes combo from Firebase
    """
    from apps.core.constants import UNIT_STATUS_AVAILABLE
    from apps.integrations.firebase_client import firebase_service

    if current_time is None:
        current_time = utcnow()

    # Find combos past their listing_end_date that are still active
    active_statuses = [COMBO_STATUS_SELLING]
    expired_combos_stmt = select(Combo).where(
        col(Combo.status).in_(active_statuses),
        col(Combo.listing_end_date).isnot(None),
        col(Combo.listing_end_date) < current_time,
    )

    expired_combos = list(db.exec(expired_combos_stmt))
    for combo in expired_combos:
        try:
            combo.status = COMBO_STATUS_EXPIRED
            combo.updated_at = current_time
            db.add(combo)

            if combo.shop_id:
                from apps.shops.crud import get_shop_with_users

                shop = get_shop_with_users(db, combo.shop_id)
                if shop:
                    users_to_notify = shop.get_all_shop_users()
                    for user in users_to_notify:
                        send_combo_expired_notification(combo, user)

            complete_reservation_and_release_locker(db, str(combo.id))

            # Delete combo from Firebase
            firebase_service.delete_combo(str(combo.id))

        except Exception:
            continue

    db.commit()
