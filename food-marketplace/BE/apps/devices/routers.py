from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlmodel import Session

from apps.core.database import get_session
from apps.core.schemas import SuccessResponse
from apps.auth.permissions import AuthenticatedUser
from apps.devices.crud import upsert_device, deactivate_token

router = APIRouter(prefix="/devices", tags=["Устройства"])


class DeviceRegisterRequest(BaseModel):
    fcm_token: str
    platform: str = "web"


@router.post("", response_model=SuccessResponse)
def register_device(body: DeviceRegisterRequest, current_user: AuthenticatedUser, db: Session = Depends(get_session)):
    upsert_device(db, current_user.id, body.fcm_token, body.platform)
    return SuccessResponse(message="Устройство зарегистрировано")


@router.delete("/{fcm_token}", response_model=SuccessResponse)
def remove_device(fcm_token: str, current_user: AuthenticatedUser, db: Session = Depends(get_session)):
    deactivate_token(db, fcm_token, current_user.id)
    return SuccessResponse(message="Устройство удалено")
