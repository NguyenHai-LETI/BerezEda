import uuid
from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel
from sqlalchemy import JSON
from apps.core.utils import utcnow


class ProductMaster(SQLModel, table=True):
    __tablename__ = "product_masters"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, max_length=36)
    shop_id: str = Field(max_length=36, index=True)
    name: str = Field(max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    images: Optional[list] = Field(default=None, sa_type=JSON)  # JSON array of image URLs
    weight_grams: int = Field(default=0)
    original_price: int = Field(default=0)
    additives: Optional[str] = Field(default=None, max_length=1000)
    nutrition_facts: Optional[str] = Field(default=None, max_length=2000)
    expiration_date_type: Optional[str] = Field(default=None, max_length=100)
    ingredients: Optional[str] = Field(default=None, max_length=1000)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
