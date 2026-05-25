from typing import Optional

from sqlmodel import Session

from apps.devices import crud
from apps.devices.exceptions import (
    device_not_found,
    device_token_exists,
    invalid_platform,
    unauthorized_device_access,
)
from apps.devices.models import Device
from apps.users.models.users import User


def validate_platform(platform: str) -> None:
    """Validate that the platform is valid."""
    if platform not in Device.PLATFORM_CHOICES:
        raise invalid_platform()


def validate_device_token_uniqueness(
    device_token: str, db: Session, exclude_id: Optional[str] = None
) -> None:
    """Validate that device token is unique."""
    existing_device = crud.get_device_by_token(db, device_token)
    if existing_device and (
        exclude_id is None or str(existing_device.id) != exclude_id
    ):
        raise device_token_exists()


def validate_device_exists(device: Device | None) -> None:
    """Validate that device exists."""
    if not device:
        raise device_not_found()


def validate_device_ownership(device: Device, user: User) -> None:
    """Validate that user owns the device or is admin."""
    if user.role != "admin" and str(device.user_id) != str(user.id):
        raise unauthorized_device_access()


def validate_device_access(device: Device, user: User) -> None:
    """Validate that user can access the device."""
    validate_device_exists(device)
    validate_device_ownership(device, user)
