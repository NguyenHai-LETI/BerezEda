import logging
from datetime import datetime, timezone
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore

from apps.core.utils import utcnow

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(
    jobstores={"default": MemoryJobStore()},
    job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": None},
    timezone=timezone.utc,
)


def expire_combo(combo_id: str):
    """Expire a combo: update status, complete reservation, release locker, sync Firebase."""
    try:
        from apps.core.database import get_sync_session
        from apps.core.constants import (
            COMBO_STATUS_EXPIRED, COMBO_STATUS_SELLING,
            UNIT_STATUS_AVAILABLE,
        )
        from apps.notifications.utils import complete_reservation_and_release_locker
        from apps.integrations.firebase_client import firebase_service

        with get_sync_session() as db:
            from apps.combos.models import Combo as ComboSimple

            combo = db.get(ComboSimple, combo_id)
            if not combo:
                logger.warning(f"expire_combo: combo {combo_id} not found")
                return

            # Only expire combos that are still active
            active_statuses = {"available", COMBO_STATUS_SELLING}
            if combo.status not in active_statuses:
                logger.info(f"expire_combo: combo {combo_id} status={combo.status}, skip")
                return

            locker_unit_id = combo.locker_unit_id

            # 1. Update combo status to EXPIRED
            combo.status = COMBO_STATUS_EXPIRED
            combo.updated_at = utcnow()
            db.add(combo)
            db.commit()

            # 2. Complete reservations (if any) + release locker unit + sync Firebase
            updated_units, synced_locations = complete_reservation_and_release_locker(db, combo_id)

            # 3. Fallback: if no reservation was found but combo had a locker_unit,
            #    release the unit directly (simple flow doesn't create LockerReservation)
            if updated_units == 0 and locker_unit_id:
                from apps.lockers.models.locker import LockerUnit

                unit = db.get(LockerUnit, locker_unit_id)
                if unit:
                    if unit.status != UNIT_STATUS_AVAILABLE:
                        unit.status = UNIT_STATUS_AVAILABLE
                        db.add(unit)
                        db.commit()
                    # Always sync Firebase regardless of DB state — Firestore may be stale
                    firebase_service.sync_locker_unit(
                        unit.location_id, unit.id,
                        {"id": unit.id, "unit_number": unit.unit_number,
                         "status": UNIT_STATUS_AVAILABLE, "is_active": unit.is_active},
                    )
                    logger.info(f"Fallback: released unit {locker_unit_id} directly")

            # 4. Delete combo from Firebase
            firebase_service.delete_combo(combo_id)

            logger.info(f"Combo {combo_id} expired — released {updated_units} units")
    except Exception as e:
        logger.error(f"expire_combo error for {combo_id}: {e}")


def cancel_ready_combo(combo_id: str):
    """Auto-cancel a combo stuck in 'ready' state — seller never placed items in the locker."""
    try:
        from apps.core.database import get_sync_session
        from apps.integrations.firebase_client import firebase_service

        with get_sync_session() as db:
            from apps.combos.models import Combo as ComboModel

            combo = db.get(ComboModel, combo_id)
            if not combo:
                logger.warning(f"cancel_ready_combo: combo {combo_id} not found")
                return

            if combo.status != "ready":
                logger.info(f"cancel_ready_combo: combo {combo_id} status={combo.status}, skip")
                return

            locker_unit_id = combo.locker_unit_id

            combo.status = "cancelled"
            combo.updated_at = utcnow()
            db.add(combo)
            db.commit()

            if locker_unit_id:
                from apps.lockers.models.locker import LockerUnit
                unit = db.get(LockerUnit, locker_unit_id)
                if unit:
                    unit.status = "AVAILABLE"
                    unit.updated_at = utcnow()
                    db.add(unit)
                    db.commit()
                    firebase_service.sync_locker_unit(
                        unit.location_id, unit.id,
                        {"id": unit.id, "unit_number": unit.unit_number,
                         "status": "AVAILABLE", "is_active": unit.is_active},
                    )

            firebase_service.delete_combo(combo_id)
            logger.info(f"Combo {combo_id} auto-cancelled (ready timeout) — released unit {locker_unit_id}")
    except Exception as e:
        logger.error(f"cancel_ready_combo error for {combo_id}: {e}")


def schedule_ready_cancel(combo_id: str, cancel_at: datetime) -> str:
    job_id = f"combo_ready_cancel_{combo_id}"
    try:
        scheduler.add_job(
            cancel_ready_combo,
            trigger="date",
            run_date=cancel_at,
            args=[combo_id],
            id=job_id,
            replace_existing=True,
        )
        logger.info(f"Scheduled ready-cancel {combo_id} at {cancel_at}")
    except Exception as e:
        logger.error(f"Failed to schedule ready-cancel: {e}")
    return job_id


def cancel_ready_cancel(combo_id: str):
    try:
        scheduler.remove_job(f"combo_ready_cancel_{combo_id}")
    except Exception:
        pass


def expire_order(order_id: str):
    try:
        from apps.core.database import get_sync_session
        from sqlmodel import select
        from apps.orders.models import Order
        from apps.lockers.services import mark_unit_available

        with get_sync_session() as db:
            order = db.exec(select(Order).where(Order.id == order_id)).first()
            if not order or order.status != "paid":
                return

            order.status = "expired"
            order.updated_at = utcnow()
            db.add(order)
            db.commit()
            logger.info(f"Order {order_id} expired (pickup deadline passed)")

            # Release the locker unit so it becomes available for the next combo
            try:
                mark_unit_available(db, order.locker_unit_id)
                logger.info(f"Released locker unit {order.locker_unit_id} after order {order_id} expiry")
            except Exception as unit_err:
                logger.error(f"Failed to release unit {order.locker_unit_id}: {unit_err}")

            # Notify customer that pickup window has closed
            try:
                from apps.notifications.services.to_user import notify_order_expired
                notify_order_expired(db, order_id, order.customer_id)
            except Exception:
                pass
    except Exception as e:
        logger.error(f"expire_order error for {order_id}: {e}")


def schedule_combo_expiry(combo_id: str, expire_at: datetime) -> str:
    job_id = f"combo_expire_{combo_id}"
    try:
        scheduler.add_job(
            expire_combo,
            trigger="date",
            run_date=expire_at,
            args=[combo_id],
            id=job_id,
            replace_existing=True,
        )
        logger.info(f"Scheduled combo expiry {combo_id} at {expire_at}")
    except Exception as e:
        logger.error(f"Failed to schedule combo expiry: {e}")
    return job_id


def cancel_combo_expiry(combo_id: str):
    job_id = f"combo_expire_{combo_id}"
    try:
        scheduler.remove_job(job_id)
    except Exception:
        pass


def schedule_order_expiry(order_id: str, expire_at: datetime) -> str:
    job_id = f"order_expire_{order_id}"
    try:
        scheduler.add_job(
            expire_order,
            trigger="date",
            run_date=expire_at,
            args=[order_id],
            id=job_id,
            replace_existing=True,
        )
    except Exception as e:
        logger.error(f"Failed to schedule order expiry: {e}")
    return job_id


def cancel_order_expiry(order_id: str):
    try:
        scheduler.remove_job(f"order_expire_{order_id}")
    except Exception:
        pass


def reschedule_all_on_startup():
    try:
        from apps.core.database import get_sync_session
        from apps.core.constants import (
            COMBO_STATUS_SELLING, COMBO_STATUS_EXPIRED,
        )
        from apps.combos.models import Combo
        from apps.orders.models import Order
        from sqlmodel import select, or_
        from datetime import datetime

        now = utcnow()
        with get_sync_session() as db:
            # ── Repair stale OCCUPIED/RESERVED units with no active combo ──
            from apps.lockers.models.unit import LockerUnit
            ACTIVE_STATUSES = {"available", "ready", COMBO_STATUS_SELLING}
            stale_units = db.exec(
                select(LockerUnit).where(LockerUnit.status.in_(["OCCUPIED", "RESERVED"]))
            ).all()
            repaired = 0
            for unit in stale_units:
                active = db.exec(
                    select(Combo).where(
                        Combo.locker_unit_id == unit.id,
                        Combo.status.in_(ACTIVE_STATUSES),
                    )
                ).first()
                if not active:
                    unit.status = "AVAILABLE"
                    unit.updated_at = now
                    db.add(unit)
                    repaired += 1
                    logger.warning(f"Repaired stale unit {unit.id} unit_number={unit.unit_number}: no active combo found")
            if repaired:
                db.commit()
                logger.info(f"Repaired {repaired} stale locker units on startup")

            # ── Ready combos: reschedule future cancels, immediately cancel overdue ──
            ready_combos = db.exec(
                select(Combo).where(
                    Combo.status == "ready",
                    Combo.ready_deadline.isnot(None),
                )
            ).all()
            ready_rescheduled = 0
            ready_cancelled = 0
            for combo in ready_combos:
                if combo.ready_deadline > now:
                    schedule_ready_cancel(combo.id, combo.ready_deadline)
                    ready_rescheduled += 1
                else:
                    cancel_ready_combo(str(combo.id))
                    ready_cancelled += 1

            # ── Reschedule future combos ──
            active_combos = db.exec(
                select(Combo).where(
                    Combo.status.in_(["available", COMBO_STATUS_SELLING]),
                    Combo.sale_end_time > now,
                )
            ).all()
            for combo in active_combos:
                schedule_combo_expiry(combo.id, combo.sale_end_time)

            # ── Immediately expire combos whose sale_end_time already passed ──
            missed_combos = db.exec(
                select(Combo).where(
                    Combo.status.in_(["available", COMBO_STATUS_SELLING]),
                    Combo.sale_end_time <= now,
                    Combo.sale_end_time.isnot(None),
                )
            ).all()
            for combo in missed_combos:
                expire_combo(str(combo.id))

            # ── Orders: schedule future expiry ──
            paid_orders = db.exec(
                select(Order).where(Order.status == "paid", Order.pickup_deadline > now)
            ).all()
            for order in paid_orders:
                schedule_order_expiry(order.id, order.pickup_deadline)

            # ── Orders: immediately expire missed orders (deadline already passed) ──
            missed_orders = db.exec(
                select(Order).where(
                    Order.status == "paid",
                    Order.pickup_deadline <= now,
                    Order.pickup_deadline.isnot(None),
                )
            ).all()
            for order in missed_orders:
                expire_order(str(order.id))

        logger.info(
            f"Ready combos: rescheduled={ready_rescheduled}, cancelled={ready_cancelled}; "
            f"Active combos rescheduled={len(active_combos)}, expired={len(missed_combos)}; "
            f"Orders rescheduled={len(paid_orders)}, expired={len(missed_orders)}"
        )
    except Exception as e:
        logger.error(f"reschedule_all_on_startup error: {e}")
