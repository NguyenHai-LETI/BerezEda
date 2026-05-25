from typing import List, Optional, Tuple

from sqlmodel import Session, select

from apps.core.utils import get_current_time
from apps.devices.models import Device


def create_device(db: Session, device: Device) -> Device:
    """Create a new device record."""
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


def get_device(db: Session, device_id: str) -> Optional[Device]:
    """Get device by ID."""
    return db.exec(select(Device).where(Device.id == device_id)).first()


def get_device_by_token(db: Session, device_token: str) -> Optional[Device]:
    """Get device by device token."""
    return db.exec(select(Device).where(Device.device_token == device_token)).first()


def get_devices_by_user(
    db: Session, user_id: str, limit: int = 20, offset: int = 0
) -> Tuple[List[Device], int]:
    """Get all devices for a specific user."""
    query = select(Device).where(Device.user_id == user_id)
    total_query = select(Device).where(Device.user_id == user_id)
    total = len(db.exec(total_query).all())
    devices = db.exec(query.offset(offset).limit(limit)).all()
    return list(devices), total


def get_all_devices(
    db: Session, limit: int = 20, offset: int = 0
) -> Tuple[List[Device], int]:
    """Get all devices (admin only)."""
    query = select(Device)
    total_query = select(Device)
    total = len(db.exec(total_query).all())
    devices = db.exec(query.offset(offset).limit(limit)).all()
    return list(devices), total


def update_device(db: Session, device: Device) -> Device:
    """Update device record."""
    device.updated_at = get_current_time()
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


def update_device_last_active(db: Session, device_id: str) -> Optional[Device]:
    """Update device last active timestamp."""
    device = get_device(db, device_id)
    if device:
        device.last_active = get_current_time()
        device.updated_at = get_current_time()
        db.add(device)
        db.commit()
        db.refresh(device)
    return device


def delete_device(db: Session, device: Device) -> None:
    """Delete device record."""
    db.delete(device)
    db.commit()


def delete_devices_by_user(db: Session, user_id: str) -> int:
    """Delete all devices for a user."""
    devices = db.exec(select(Device).where(Device.user_id == user_id)).all()
    count = len(devices)
    for device in devices:
        db.delete(device)
    db.commit()
    return count


def get_device_by_token_and_user(
    db: Session, device_token: str, user_id: str
) -> Optional[Device]:
    """Get device by token and user_id. If user_id is None, find device with user_id IS NULL."""
    stm = select(Device).where(
        (Device.device_token == device_token) & (Device.user_id == user_id)
    )
    return db.exec(stm).first()


def delete_device_by_token_and_user(
    db: Session, device_token: str, user_id: str
) -> bool:
    """Delete device by token and user ID. Returns True if device was found and deleted."""
    device = db.exec(
        select(Device).where(
            Device.device_token == device_token, Device.user_id == user_id
        )
    ).first()
    if device:
        db.delete(device)
        db.commit()
        return True
    return False


def update_device_user_id(db: Session, device: Device, user_id: str) -> Device:
    """Update device user_id."""
    device.user_id = user_id
    device.updated_at = get_current_time()
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


def get_all_devices_for_broadcast(db: Session) -> List[Device]:
    """
    Get all devices from database.

    Args:
        db: Database session

    Returns:
        List of all Device objects
    """
    return list(db.exec(select(Device)).all())
