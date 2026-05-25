from typing import Optional, List
from sqlmodel import Session, select

from apps.combos.models import Combo, ComboProduct
from apps.core.utils import utcnow


def get_combo_by_id(db: Session, combo_id: str) -> Optional[Combo]:
    return db.get(Combo, combo_id)


def get_available_combos(
    db: Session,
    locker_location_id: Optional[str] = None,
    shop_id: Optional[str] = None,
) -> List[Combo]:
    now = utcnow()

    # Auto-expire combos that the scheduler missed
    expired = db.exec(
        select(Combo).where(
            Combo.status == "available",
            Combo.sale_end_time <= now,
        )
    ).all()
    released_units = []
    for c in expired:
        c.status = "expired"
        c.updated_at = now
        db.add(c)
        if c.locker_unit_id:
            from apps.lockers.models import LockerUnit
            unit = db.get(LockerUnit, c.locker_unit_id)
            if unit and unit.status != "AVAILABLE":
                unit.status = "AVAILABLE"
                unit.updated_at = now
                db.add(unit)
                released_units.append(unit)
    if expired:
        db.commit()
        if released_units:
            from apps.integrations.firebase_client import firebase_service
            for unit in released_units:
                try:
                    firebase_service.sync_locker_unit(
                        unit.location_id, unit.id,
                        {
                            "id": unit.id,
                            "unit_number": unit.unit_number,
                            "status": unit.status,
                            "temperature": unit.temperature,
                            "size": unit.size,
                            "is_active": unit.is_active,
                        },
                    )
                except Exception:
                    pass

    q = select(Combo).where(
        Combo.status == "available",
        Combo.sale_end_time > now,
    )
    if locker_location_id:
        q = q.where(Combo.locker_location_id == locker_location_id)
    if shop_id:
        q = q.where(Combo.shop_id == shop_id)
    return db.exec(q.order_by(Combo.sale_end_time)).all()


def get_combos_by_shop(
    db: Session, shop_id: str,
    status: Optional[str] = None,
) -> List[Combo]:
    # Auto-cancel ready combos that the scheduler missed (e.g. after server restart)
    now = utcnow()
    overdue_ready = db.exec(
        select(Combo).where(
            Combo.shop_id == shop_id,
            Combo.status == "ready",
            Combo.ready_deadline.isnot(None),
            Combo.ready_deadline <= now,
        )
    ).all()
    if overdue_ready:
        from apps.lockers.models import LockerUnit
        from apps.integrations.firebase_client import firebase_service
        for c in overdue_ready:
            c.status = "cancelled"
            c.updated_at = now
            db.add(c)
            if c.locker_unit_id:
                unit = db.get(LockerUnit, c.locker_unit_id)
                if unit and unit.status != "AVAILABLE":
                    unit.status = "AVAILABLE"
                    unit.updated_at = now
                    db.add(unit)
        db.commit()
        for c in overdue_ready:
            try:
                firebase_service.delete_combo(c.id)
            except Exception:
                pass
            if c.locker_unit_id:
                try:
                    from apps.lockers.models import LockerUnit
                    unit = db.get(LockerUnit, c.locker_unit_id)
                    if unit:
                        firebase_service.sync_locker_unit(
                            unit.location_id, unit.id,
                            {"id": unit.id, "unit_number": unit.unit_number,
                             "status": "AVAILABLE", "is_active": unit.is_active},
                        )
                except Exception:
                    pass

    q = select(Combo).where(Combo.shop_id == shop_id)
    if status:
        q = q.where(Combo.status == status)
    return db.exec(q.order_by(Combo.created_at.desc())).all()


def get_combo_products(db: Session, combo_id: str) -> List[ComboProduct]:
    return db.exec(select(ComboProduct).where(ComboProduct.combo_id == combo_id)).all()


def create_combo(db: Session, shop_id: str, data: dict, products: list) -> Combo:
    combo = Combo(shop_id=shop_id, **data)
    db.add(combo)
    db.flush()
    for p in products:
        cp = ComboProduct(combo_id=combo.id, **p)
        db.add(cp)
    db.commit()
    db.refresh(combo)
    return combo





def update_combo(db: Session, combo: Combo, data: dict) -> Combo:
    for k, v in data.items():
        setattr(combo, k, v)
    combo.updated_at = utcnow()
    db.add(combo)
    db.commit()
    db.refresh(combo)
    return combo


def mark_combo_sold(db: Session, combo: Combo) -> Combo:
    combo.status = "sold"
    combo.updated_at = utcnow()
    db.add(combo)
    db.commit()
    db.refresh(combo)
    return combo
