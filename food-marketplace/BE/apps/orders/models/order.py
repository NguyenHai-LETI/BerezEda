import secrets
import string
import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel
from apps.core.utils import utcnow


def generate_order_number() -> str:
    """ORD{YYYYMMDDHHmmss}{4 random digits} — e.g. ORD202603211430001234"""
    timestamp = utcnow().strftime("%Y%m%d%H%M%S")
    suffix = "".join(secrets.choice(string.digits) for _ in range(4))
    return f"ORD{timestamp}{suffix}"


class Order(SQLModel, table=True):
    __tablename__ = "orders"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, max_length=36)
    customer_id: str = Field(max_length=36, index=True)
    combo_id: str = Field(max_length=36, index=True)
    shop_id: str = Field(max_length=36, index=True)
    locker_unit_id: str = Field(max_length=36)
    locker_location_id: str = Field(max_length=36)
    order_number: str = Field(default_factory=generate_order_number, unique=True, index=True, max_length=50)
    status: str = Field(default="pending", max_length=20, index=True)
    amount: int
    original_amount: int
    discount_rate: int
    access_code: str = Field(max_length=10)
    fincode_payment_id: Optional[str] = Field(default=None, max_length=100)
    fincode_order_id: Optional[str] = Field(default=None, max_length=100)
    pickup_deadline: Optional[datetime] = Field(default=None)
    paid_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
