from typing import Optional, List
import json
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    weight_grams: int = Field(default=0, ge=0)
    original_price: int = Field(ge=0)
    images: Optional[List[str]] = None
    additives: Optional[str] = None
    nutrition_facts: Optional[str] = None
    expiration_date_type: Optional[str] = None
    ingredients: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    weight_grams: Optional[int] = None
    original_price: Optional[int] = None
    images: Optional[List[str]] = None
    additives: Optional[str] = None
    nutrition_facts: Optional[str] = None
    expiration_date_type: Optional[str] = None
    ingredients: Optional[str] = None
    is_active: Optional[bool] = None


class ProductResponse(BaseModel):
    id: str
    shop_id: str
    name: str
    description: Optional[str] = None
    images: Optional[List[str]] = None
    weight_grams: int
    original_price: int
    additives: Optional[str] = None
    nutrition_facts: Optional[str] = None
    expiration_date_type: Optional[str] = None
    ingredients: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @field_validator('images', mode='before')
    @classmethod
    def parse_images(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else None
            except (json.JSONDecodeError, TypeError):
                return None
        return v

    class Config:
        from_attributes = True
