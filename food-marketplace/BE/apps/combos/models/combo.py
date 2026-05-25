import uuid
from datetime import date, datetime
from typing import Optional
from sqlmodel import Field, SQLModel
from apps.core.utils import utcnow


class Combo(SQLModel, table=True):
    __tablename__ = "combo"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, max_length=36)
    shop_id: str = Field(max_length=36, index=True)
    locker_unit_id: Optional[str] = Field(default=None, max_length=36, index=True)
    locker_location_id: Optional[str] = Field(default=None, max_length=36, index=True)
    title: str = Field(max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    discount_rate: int = Field(default=30)
    original_price: int = Field(default=0)
    sale_price: int = Field(default=0)
    weight_grams: int = Field(default=0)
    status: str = Field(default="draft", max_length=20, index=True)
    sale_start_time: Optional[datetime] = Field(default=None)
    sale_end_time: Optional[datetime] = Field(default=None)
    sale_duration_hours: int = Field(default=3)
    image: Optional[str] = Field(default=None, max_length=500)
    access_code: Optional[str] = Field(default=None, max_length=10)
    scheduled_expiry_job_id: Optional[str] = Field(default=None, max_length=100)
    ready_deadline: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class ComboProduct(SQLModel, table=True):
    __tablename__ = "combo_products"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, max_length=36)
    combo_id: str = Field(max_length=36, index=True)
    product_id: str = Field(max_length=36)
    quantity: int = Field(default=1)
    expiry_date: Optional[date] = Field(default=None)
