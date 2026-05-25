from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel, Field


class ComboProductItem(BaseModel):
    product_id: str
    quantity: int = Field(default=1, ge=1)
    expiry_date: Optional[date] = None


class ComboCreate(BaseModel):
    """Create combo draft — locker unit is NOT required at this stage."""
    title: str
    description: Optional[str] = None
    discount_rate: int = Field(default=30, ge=10, le=90)
    sale_duration_hours: int = Field(default=3, ge=1, le=48)
    products: List[ComboProductItem]
    # Optional: allow setting locker at creation if caller wants to
    locker_unit_id: Optional[str] = None
    locker_location_id: Optional[str] = None


class ComboAssignLocker(BaseModel):
    """Assign locker unit before publishing (step 3 of publish flow)."""
    locker_unit_id: str
    locker_location_id: str


class ComboUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    discount_rate: Optional[int] = Field(default=None, ge=10, le=90)
    sale_duration_hours: Optional[int] = Field(default=None, ge=1, le=48)


class ComboProductResponse(BaseModel):
    id: str
    product_id: str
    quantity: int
    expiry_date: Optional[date] = None
    product_name: Optional[str] = None
    product_image: Optional[str] = None

    class Config:
        from_attributes = True


class ComboLockerInfo(BaseModel):
    locker_name: Optional[str] = None
    locker_address: Optional[str] = None
    unit_number: Optional[int] = None
    locker_lat: Optional[float] = None
    locker_lng: Optional[float] = None


class ComboResponse(BaseModel):
    id: str
    shop_id: str
    locker_unit_id: Optional[str] = None
    locker_location_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    discount_rate: int
    original_price: int
    sale_price: int
    weight_grams: int
    status: str
    sale_start_time: Optional[datetime] = None
    sale_end_time: Optional[datetime] = None
    sale_duration_hours: int
    image: Optional[str] = None
    shop_name: Optional[str] = None
    shop_avg_rating: float = 0.0
    shop_total_reviews: int = 0
    access_code: Optional[str] = None
    ready_deadline: Optional[datetime] = None
    products: List[ComboProductResponse] = []
    locker_info: Optional[ComboLockerInfo] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
