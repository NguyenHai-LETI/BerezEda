from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


# ── Request schemas ──────────────────────────────────────────────────────────

class PaymentRequest(BaseModel):
    order_id: str
    card_id: str   # local Card.id (from our DB)


class PaymentChangeRequest(BaseModel):
    order_id: str


# ── Response schemas ─────────────────────────────────────────────────────────

class CardResponse(BaseModel):
    id: str
    fincode_card_id: str
    card_number_masked: str
    brand: str
    expire: str
    holder_name: Optional[str] = None
    is_default: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserCardInfo(BaseModel):
    """Card info fetched directly from Fincode API."""
    id: str
    fincode_card_id: str
    card_number_masked: str
    brand: str
    expire: str
    holder_name: str
    is_default: bool


class CardSessionResponse(BaseModel):
    card_registration_url: str


class PaymentResponse(BaseModel):
    id: str
    order_id: str
    status: str
    amount: int
    created_at: datetime

    class Config:
        from_attributes = True


class FincodeCustomerResponse(BaseModel):
    fincode_customer_id: str
