import random
from datetime import timedelta
from typing import List
from sqlmodel import Session

from apps.combos import crud
from apps.combos.exceptions import (
    combo_not_found, combo_access_denied, combo_not_draft,
    combo_not_available, no_products, combo_no_locker, combo_not_ready,
)
from apps.combos.models import Combo
from apps.lockers.services import get_unit_or_404, assert_available, mark_unit_available
from apps.core.utils import utcnow
from apps.products.crud import get_product_by_id
from apps.integrations.firebase_client import firebase_service


def get_combo_or_404(db: Session, combo_id: str) -> Combo:
    combo = crud.get_combo_by_id(db, combo_id)
    if not combo:
        raise combo_not_found()
    return combo


def assert_shop_owner(combo: Combo, shop_id: str):
    if combo.shop_id != shop_id:
        raise combo_access_denied()


def _calc_prices(db: Session, products_data: list, discount_rate: int):
    original_price = 0
    weight_grams = 0
    for p in products_data:
        product = get_product_by_id(db, p["product_id"])
        if product:
            original_price += product.original_price * p["quantity"]
            weight_grams += product.weight_grams * p["quantity"]
    sale_price = int(original_price * (1 - discount_rate / 100))
    return original_price, sale_price, weight_grams


def create_combo(db: Session, shop_id: str, data: dict) -> Combo:
    """Create a draft combo. locker_unit_id is optional."""
    products_data = data.pop("products", [])
    if not products_data:
        raise no_products()

    original_price, sale_price, weight_grams = _calc_prices(
        db, products_data, data.get("discount_rate", 30)
    )

    # If locker_unit_id provided, validate availability
    if data.get("locker_unit_id"):
        unit = get_unit_or_404(db, data["locker_unit_id"])
        assert_available(unit)

    combo_data = {k: v for k, v in data.items() if k != "products"}
    combo_data["original_price"] = original_price
    combo_data["sale_price"] = sale_price
    combo_data["weight_grams"] = weight_grams

    return crud.create_combo(db, shop_id, combo_data, products_data)


def assign_locker(db: Session, combo_id: str, shop_id: str, locker_unit_id: str, locker_location_id: str) -> Combo:
    """Step 3 of publish flow: assign locker unit and generate access code.
    Returns combo with access_code (AA QR code) visible to seller. Status → 'ready'.
    """
    import httpx
    from apps.core.config import LOCKER_SIM_URL, COMBO_READY_TIMEOUT_MINUTES
    from apps.lockers.models import LockerUnit
    from apps.scheduler.scheduler import schedule_ready_cancel

    combo = get_combo_or_404(db, combo_id)
    assert_shop_owner(combo, shop_id)
    if combo.status != "draft":
        raise combo_not_draft()

    unit = get_unit_or_404(db, locker_unit_id)
    assert_available(unit)

    now = utcnow()
    ready_deadline = now + timedelta(minutes=COMBO_READY_TIMEOUT_MINUTES)

    # Atomic: mark unit RESERVED + update combo in single commit
    unit.status = "RESERVED"
    unit.updated_at = now
    db.add(unit)

    combo.locker_unit_id = locker_unit_id
    combo.locker_location_id = locker_location_id
    combo.access_code = f"AA{random.randint(100000, 999999):06d}"
    combo.status = "ready"
    combo.ready_deadline = ready_deadline
    combo.updated_at = now
    db.add(combo)
    db.commit()
    db.refresh(combo)

    schedule_ready_cancel(combo.id, ready_deadline)

    # Sync unit to Firebase (non-critical)
    try:
        firebase_service.sync_locker_unit(
            unit.location_id, unit.id,
            {"id": unit.id, "unit_number": unit.unit_number,
             "status": "RESERVED", "is_active": unit.is_active},
        )
    except Exception:
        pass

    # Register AA deposit code in System 2
    try:
        res = httpx.post(
            f"{LOCKER_SIM_URL}/locker-codes/register-deposit",
            json={"locker_unit_id": locker_unit_id, "location_id": locker_location_id, "combo_id": combo.id},
            timeout=5.0,
        )
        if res.status_code == 200:
            aa_code = res.json().get("data", {}).get("code")
            if aa_code:
                combo.access_code = aa_code
                combo.updated_at = now
                db.add(combo)
                db.commit()
                db.refresh(combo)
    except Exception:
        pass  # System 2 unavailable — combo.access_code keeps the random 6-digit fallback

    return combo


def confirm_placed(db: Session, combo_id: str, shop_id: str) -> Combo:
    """Step 5 of publish flow: seller simulates placing item → status = available (SELLING)."""
    from apps.lockers.models import LockerUnit
    from apps.scheduler.scheduler import schedule_combo_expiry, cancel_ready_cancel

    combo = get_combo_or_404(db, combo_id)
    assert_shop_owner(combo, shop_id)

    if combo.status not in ("draft", "ready"):
        raise combo_not_draft()
    if not combo.locker_unit_id:
        raise combo_no_locker()

    cancel_ready_cancel(combo_id)

    now = utcnow()
    unit = db.get(LockerUnit, combo.locker_unit_id)

    # Atomic: mark unit OCCUPIED + publish combo in single commit
    if unit:
        unit.status = "OCCUPIED"
        unit.updated_at = now
        db.add(unit)

    combo.status = "available"
    combo.sale_start_time = now
    combo.sale_end_time = now + timedelta(hours=combo.sale_duration_hours)
    combo.access_code = str(random.randint(100000, 999999))
    combo.updated_at = now
    db.add(combo)
    db.commit()
    db.refresh(combo)

    # Sync unit to Firebase (non-critical)
    if unit:
        try:
            firebase_service.sync_locker_unit(
                unit.location_id, unit.id,
                {"id": unit.id, "unit_number": unit.unit_number,
                 "status": "OCCUPIED", "is_active": unit.is_active},
            )
        except Exception:
            pass

    # Schedule expiry
    job_id = schedule_combo_expiry(combo.id, combo.sale_end_time)
    combo.scheduled_expiry_job_id = job_id
    db.add(combo)
    db.commit()
    db.refresh(combo)

    # Notify followers
    try:
        from apps.notifications.services import notify_combo_available
        from apps.shops.crud import get_shop_by_id
        from apps.lockers.crud import get_location_by_id
        shop = get_shop_by_id(db, combo.shop_id)
        location = get_location_by_id(db, combo.locker_location_id) if combo.locker_location_id else None
        notify_combo_available(
            db, str(combo.id),
            shop.name if shop else "",
            location.name if location else "",
            location.address if location else "",
        )
    except Exception:
        pass

    firebase_service.sync_combo(combo.id, {
        "id": combo.id, "shop_id": combo.shop_id,
        "locker_unit_id": combo.locker_unit_id,
        "locker_location_id": combo.locker_location_id,
        "title": combo.title, "sale_price": combo.sale_price,
        "status": combo.status,
        "sale_end_time": combo.sale_end_time.isoformat() if combo.sale_end_time else None,
    })
    return combo


def cancel_combo(db: Session, combo_id: str, shop_id: str) -> Combo:
    from apps.lockers.models import LockerUnit
    from apps.scheduler.scheduler import cancel_combo_expiry, cancel_ready_cancel

    combo = get_combo_or_404(db, combo_id)
    assert_shop_owner(combo, shop_id)

    unit = None
    if combo.locker_unit_id and combo.status in ("available", "ready"):
        unit = db.get(LockerUnit, combo.locker_unit_id)
        if combo.status == "available":
            cancel_combo_expiry(combo.id)
        else:
            cancel_ready_cancel(combo.id)

    # Atomic: release unit + cancel combo in single commit
    if unit:
        unit.status = "AVAILABLE"
        unit.updated_at = utcnow()
        db.add(unit)

    combo.status = "cancelled"
    combo.updated_at = utcnow()
    db.add(combo)
    db.commit()
    db.refresh(combo)

    firebase_service.delete_combo(combo.id)

    if unit:
        try:
            firebase_service.sync_locker_unit(unit.location_id, unit.id, {
                "id": unit.id, "location_id": unit.location_id,
                "unit_number": unit.unit_number, "status": "AVAILABLE",
                "is_active": unit.is_active,
            })
        except Exception:
            pass

    return combo
