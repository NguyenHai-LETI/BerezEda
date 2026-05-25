from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


class OrderCreate(BaseModel):
    combo_id: str
    card_id: Optional[str] = None


class OrderResponse(BaseModel):
    id: str
    customer_id: str
    combo_id: str
    shop_id: str
    locker_unit_id: str
    locker_location_id: str
    status: str
    amount: int
    original_amount: int
    discount_rate: int
    access_code: str
    fincode_payment_id: Optional[str] = None
    pickup_deadline: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FincodeWebhookPayload(BaseModel):
    id: Optional[str] = None
    pay_type: Optional[str] = None
    status: Optional[str] = None
    amount: Optional[str] = None
    order_id: Optional[str] = None

    class Config:
        extra = "allow"


class PickupRequest(BaseModel):
    access_code: str


class LockerSimLookupRequest(BaseModel):
    access_code: str
