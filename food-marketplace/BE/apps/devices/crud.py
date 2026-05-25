from typing import List, Optional
from sqlmodel import Session, select
from apps.devices.models import Device
from apps.core.utils import utcnow


def get_tokens_by_user(db: Session, user_id: str) -> List[str]:
    devices = db.exec(
        select(Device).where(Device.user_id == user_id, Device.is_active == True)
    ).all()
    return [d.fcm_token for d in devices]


def get_all_tokens_for_users(db: Session, user_ids: List[str]) -> List[str]:
    if not user_ids:
        return []
    devices = db.exec(
        select(Device).where(Device.user_id.in_(user_ids), Device.is_active == True)
    ).all()
    return [d.fcm_token for d in devices]


def upsert_device(db: Session, user_id: str, fcm_token: str, platform: str = "web") -> Device:
    existing = db.exec(
        select(Device).where(Device.fcm_token == fcm_token)
    ).first()
    if existing:
        existing.user_id = user_id
        existing.is_active = True
        existing.updated_at = utcnow()
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing
    device = Device(user_id=user_id, fcm_token=fcm_token, platform=platform)
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


def deactivate_token(db: Session, fcm_token: str, user_id: str) -> None:
    device = db.exec(
        select(Device).where(Device.fcm_token == fcm_token, Device.user_id == user_id)
    ).first()
    if device:
        device.is_active = False
        device.updated_at = utcnow()
        db.add(device)
        db.commit()
