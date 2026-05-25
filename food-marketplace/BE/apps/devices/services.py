from typing import Optional

from sqlmodel import Session

from apps.devices import crud, schemas
from apps.devices.models import Device
from apps.devices.validators import (
    validate_device_exists,
    validate_device_ownership,
    validate_platform,
)
from apps.users.models.users import User


def create_device_service(
    device: schemas.DeviceCreate, user: Optional[User], db: Session
):
    # Validate platform
    validate_platform(device.platform)

    user_id = user.id if user else None

    # Check if device with same token already exists for this user (or no user)
    existing_device = crud.get_device_by_token(db, device.device_token)

    if existing_device:
        # Update existing device instead of creating new one
        existing_device.platform = device.platform
        existing_device.position = device.position
        existing_device.user_id = user_id
        device_obj = crud.update_device(db, existing_device)
    else:
        # Create new device with user_id = None
        device_data = device.model_dump()
        device_data["user_id"] = None
        new_device = Device(**device_data)
        device_obj = crud.create_device(db, new_device)

    return schemas.DeviceRead.model_validate(device_obj, from_attributes=True)


def update_device_service(device: schemas.DeviceUpdate, user: User, db: Session):
    """
    Update device user_id by device_token.

    Args:
        device: DeviceUpdate schema containing device_token
        user: Authenticated user (required)
        db: Database session

    Returns:
        DeviceRead schema
    """
    # Get device by token
    device_obj = crud.get_device_by_token(db, device.device_token)
    validate_device_exists(device_obj)

    # Update device.user_id = user.id
    device_obj = crud.update_device_user_id(db, device_obj, str(user.id))

    return schemas.DeviceRead.model_validate(device_obj, from_attributes=True)


def delete_device_service(device_id: str, user: User, db: Session):
    """Delete device with access control."""
    device = crud.get_device(db, device_id)
    validate_device_exists(device)
    # After validation, device is guaranteed to exist
    assert device is not None
    validate_device_ownership(device, user)

    crud.delete_device(db, device)
    return None


def unlink_device_from_user_service(device_token: str, user_id: str, db: Session):
    """
    Unlink a device from a user by setting user_id = None.
    Only unlinks if the device belongs to the specified user.

    Args:
        device_token: Device token to search for
        user_id: User ID to verify device ownership
        db: Database session

    Returns:
        True if device was found and unlinked, False otherwise
    """
    device = crud.get_device_by_token_and_user(db, device_token, user_id)

    if device:
        crud.update_device_user_id(db, device, None)
    return None
