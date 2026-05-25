from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class RegisterDepositRequest(BaseModel):
    locker_unit_id: str
    location_id: str
    combo_id: str


class RegisterPickupRequest(BaseModel):
    locker_unit_id: str
    location_id: str
    combo_id: str
    order_id: str
    expires_at: Optional[datetime] = None


class LockerCodeResponse(BaseModel):
    code: str
    code_type: str
    numeric_part: str
    locker_unit_id: str
    location_id: str
    combo_id: Optional[str] = None
    order_id: Optional[str] = None


class ValidateQRRequest(BaseModel):
    qr_code: str


class ValidateQRResponse(BaseModel):
    valid: bool
    code_type: Optional[str] = None
    locker_unit_id: Optional[str] = None
    location_id: Optional[str] = None
    combo_id: Optional[str] = None
    order_id: Optional[str] = None
    code: Optional[str] = None
    message: str = "OK"


class SimulateActionRequest(BaseModel):
    code: str


class SimulateActionResponse(BaseModel):
    success: bool
    message: str
    system1_response: Optional[dict] = None
