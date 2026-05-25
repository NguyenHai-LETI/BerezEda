from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    order_id: str
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None


class ReviewResponse(BaseModel):
    id: str
    order_id: str
    customer_id: str
    shop_id: str
    combo_id: str
    rating: int
    comment: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
