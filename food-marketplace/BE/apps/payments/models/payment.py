import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel
from apps.core.utils import utcnow


class Payment(SQLModel, table=True):
    __tablename__ = "payments"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, max_length=36)
    order_id: str = Field(max_length=36, index=True)
    customer_id: str = Field(max_length=36, index=True)
    card_id: Optional[str] = Field(default=None, max_length=100)          # local Card.id
    fincode_payment_id: str = Field(max_length=100)                        # order_id used in Fincode
    fincode_customer_id: Optional[str] = Field(default=None, max_length=100)
    fincode_access_id: Optional[str] = Field(default=None, max_length=100) # access_id from register step
    amount: int
    status: str = Field(default="INIT", max_length=20)                    # INIT | UNPROCESSED | CAPTURED | AUTHENTICATED | FAILED
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Card(SQLModel, table=True):
    __tablename__ = "card"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, max_length=36)
    customer_id: str = Field(max_length=36, index=True)
    fincode_customer_id: str = Field(max_length=100)
    fincode_card_id: str = Field(max_length=100)
    card_number_masked: str = Field(max_length=20)
    brand: str = Field(default="", max_length=30)
    expire: str = Field(default="", max_length=10)
    holder_name: Optional[str] = Field(default=None, max_length=100)
    is_default: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utcnow)


class FincodeUser(SQLModel, table=True):
    __tablename__ = "fincode_user"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, max_length=36)
    user_id: str = Field(max_length=36, unique=True, index=True)
    fincode_customer_id: str = Field(max_length=100)
    created_at: datetime = Field(default_factory=utcnow)
