from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from apps.core.schemas import PositionParserMixin
from apps.orders.schemas import OrderDetailRead
from apps.products.schemas import LockerUnitRead


class ShopCreate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    logo: Optional[str] = None
    is_active: Optional[bool] = True
    position: Optional[str] = None
    owner_id: Optional[str] = None


class ShopRead(PositionParserMixin):
    id: str
    code: str
    name: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    logo: Optional[str] = None
    is_active: Optional[bool] = True
    avg_rating: float
    total_reviews: int
    is_favorite: bool = False  # Indicates if current user has favorited this shop
    owner_email: Optional[str] = None  # Email of the shop owner
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ShopReadWithDistance(ShopRead):
    distance: Optional[float] = None
    number_combos: Optional[int] = None
    has_selling_combos: Optional[bool] = None


class ShopPartialUpdate(BaseModel):
    """Schema for updating only phone and description fields"""

    phone: Optional[str] = None
    description: Optional[str] = None


class ShopComboRead(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    images: Optional[List[str]] = None
    is_available: bool
    original_price: Optional[float] = None
    discount_percentage: float
    product_number: Optional[str] = None
    category: Optional[str] = None
    listing_end_date: Optional[datetime] = None
    pickup_deadline: Optional[datetime] = None
    is_free: bool = False
    is_draft: bool
    is_checked: bool
    status: str
    code: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    shop_id: str

    # Countdown timer fields for app processing
    time_remaining_seconds: Optional[int] = None  # Total seconds until listing_end_date
    next_status_change_at: Optional[datetime] = None  # When status will change next

    # Discount logic fields for app
    can_be_free: Optional[bool] = None
    current_effective_price: Optional[float] = None  # Actual price user will pay now
    discounted_price: Optional[float] = None  # Price after discount_percentage applied

    model_config = {"from_attributes": True}


class SalesHistoryRead(BaseModel):
    """Schema for shop sales history response"""

    sales_end_date: Optional[datetime] = None  # sale_end_time from reservation
    status: str  # combo status
    combo_id: str  # combo id
    locker_unit: Optional[LockerUnitRead] = None  # Complete locker unit information
    combo_name: str  # combo.name
    product_number: Optional[str] = None  # combo.product_number
    is_free: bool = False  # combo.is_free
    order: Optional[OrderDetailRead] = (
        None  # Detailed order information if order exists
    )

    model_config = {"from_attributes": True}


class ShopUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    position: Optional[str] = None
    address: Optional[str] = None
    logo: Optional[str] = None
