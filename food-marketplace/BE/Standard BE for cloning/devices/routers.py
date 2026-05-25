from fastapi import APIRouter, Depends
from sqlmodel import Session

from apps.auth.permissions import AuthenticatedUser, AuthenticatedUserOrNone
from apps.core.database import get_session
from apps.core.schemas import SuccessResponse

from . import schemas, services

devices_router = APIRouter(tags=["Devices"])


@devices_router.post("/", response_model=SuccessResponse[schemas.DeviceRead])
def create_device(
    user: AuthenticatedUserOrNone,
    device: schemas.DeviceCreate,
    db: Session = Depends(get_session),
):
    """
    Create or update device registration.
    - If no user (no token): create new device with user_id = null
    - If user exists (with token): create or update device with user_id = user.id
    """
    device_obj = services.create_device_service(device, user, db)
    return SuccessResponse(data=device_obj)


@devices_router.put("/", response_model=SuccessResponse[schemas.DeviceRead])
def update_device(
    user: AuthenticatedUser,
    device: schemas.DeviceUpdate,
    db: Session = Depends(get_session),
):
    """Update device user_id by device_token for the authenticated user."""
    device_obj = services.update_device_service(device, user, db)
    return SuccessResponse(data=device_obj)


@devices_router.delete("/{device_id}", response_model=SuccessResponse[None])
def delete_device(
    user: AuthenticatedUser,
    device_id: str,
    db: Session = Depends(get_session),
):
    """Delete device with access control."""
    services.delete_device_service(device_id, user, db)
    return SuccessResponse(data=None)
