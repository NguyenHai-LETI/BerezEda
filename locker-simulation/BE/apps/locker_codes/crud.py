import random
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session, select

from apps.locker_codes.models import LockerCode


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _generate_unique_numeric(db: Session) -> str:
    for _ in range(200):
        code = f"{random.randint(100000, 999999)}"
        existing = db.exec(
            select(LockerCode).where(
                LockerCode.numeric_part == code,
                LockerCode.is_active == True,
            )
        ).first()
        if not existing:
            return code
    raise ValueError("Failed to generate unique 6-digit code")


def deactivate_codes_for_unit(db: Session, locker_unit_id: str, code_type: str) -> None:
    codes = db.exec(
        select(LockerCode).where(
            LockerCode.locker_unit_id == locker_unit_id,
            LockerCode.code_type == code_type,
            LockerCode.is_active == True,
        )
    ).all()
    for code in codes:
        code.is_active = False
        db.add(code)
    db.commit()


def create_deposit_code(db: Session, locker_unit_id: str, location_id: str, combo_id: str) -> LockerCode:
    deactivate_codes_for_unit(db, locker_unit_id, "AA")
    numeric = _generate_unique_numeric(db)
    lc = LockerCode(
        code=f"AA{numeric}",
        code_type="AA",
        numeric_part=numeric,
        locker_unit_id=locker_unit_id,
        location_id=location_id,
        combo_id=combo_id,
    )
    db.add(lc)
    db.commit()
    db.refresh(lc)
    return lc


def create_pickup_code(
    db: Session,
    locker_unit_id: str,
    location_id: str,
    combo_id: str,
    order_id: str,
    expires_at: Optional[datetime] = None,
) -> LockerCode:
    deactivate_codes_for_unit(db, locker_unit_id, "BB")
    numeric = _generate_unique_numeric(db)
    lc = LockerCode(
        code=f"BB{numeric}",
        code_type="BB",
        numeric_part=numeric,
        locker_unit_id=locker_unit_id,
        location_id=location_id,
        combo_id=combo_id,
        order_id=order_id,
        expires_at=expires_at,
    )
    db.add(lc)
    db.commit()
    db.refresh(lc)
    return lc


def get_active_code(db: Session, qr_code: str) -> Optional[LockerCode]:
    # Accept 6-digit numeric part (from QR) or full code (AA/BB + 6 digits)
    if len(qr_code) == 6 and qr_code.isdigit():
        condition = LockerCode.numeric_part == qr_code
    else:
        condition = LockerCode.code == qr_code

    lc = db.exec(
        select(LockerCode).where(condition, LockerCode.is_active == True)
    ).first()
    if not lc:
        return None
    if lc.expires_at and lc.expires_at.replace(tzinfo=timezone.utc) < utcnow():
        lc.is_active = False
        db.add(lc)
        db.commit()
        return None
    return lc


def mark_code_used(db: Session, lc: LockerCode) -> LockerCode:
    lc.is_active = False
    lc.used_at = utcnow()
    db.add(lc)
    db.commit()
    db.refresh(lc)
    return lc
