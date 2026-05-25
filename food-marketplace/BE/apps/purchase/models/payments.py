import uuid
from datetime import datetime
from typing import ClassVar, Optional

from sqlmodel import Field, SQLModel


class Payment(SQLModel, table=True):
    __tablename__: ClassVar[str] = "payments"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True,
        max_length=36,
    )
    # fields for payment regis
    order_id: Optional[str]
    pay_type: str = Field(default="Card", max_length=20)
    job_code: str = Field(default="AUTH", max_length=20)
    amount: int
    tds_type: str = Field(default="2", max_length=10)
    tds2_type: str = Field(default="2", max_length=10)
    client_field_1: Optional[str] = Field(default=None, max_length=100)

    # fields for payment exec
    card_id: Optional[str] = Field(default=None, max_length=100)
    customer_id: Optional[str] = Field(default=None, max_length=100)
    method: Optional[int] = Field(default=1, max_length=1)

    # fields get from fincode
    access_id: Optional[str] = Field(default=None, max_length=100)
    status: str = Field(max_length=50)
    created: datetime = Field(default_factory=datetime.utcnow)
    updated: datetime = Field(default_factory=datetime.utcnow)
    process_date: Optional[str] = Field(default=None)
    error_code: Optional[str] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    # 3D Secure fields
    tds2_ret_url: Optional[str] = Field(default=None, max_length=500)
    tds2_status: Optional[str] = Field(default=None, max_length=50)
    return_url: Optional[str] = Field(default=None, max_length=500)
    return_url_on_failure: Optional[str] = Field(default=None, max_length=500)
    redirect_url: Optional[str] = Field(default=None, max_length=1000)
