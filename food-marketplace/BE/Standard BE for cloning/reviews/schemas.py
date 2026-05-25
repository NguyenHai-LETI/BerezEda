from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from apps.lockers.schemas import LockerUnitRead


class UserBasicRead(BaseModel):
    """Basic user information for review responses"""

    id: str
    icon: Optional[str] = None

    model_config = {"from_attributes": True}


class ShopBasicRead(BaseModel):
    """Basic shop information for review responses"""

    id: str
    name: Optional[str] = None
    code: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None

    model_config = {"from_attributes": True}


class LockerBasicRead(BaseModel):
    """Basic locker location information for review responses"""

    id: str
    name: str
    code: Optional[str] = None
    address: Optional[str] = None
    position: Optional[str] = None

    model_config = {"from_attributes": True}



class OrderBasicRead(BaseModel):
    """Basic order information for review responses"""

    id: str
    order_number: str
    status: str
    original_price: float
    discount_percentage: float
    final_price: float
    pickup_deadline: Optional[datetime] = None
    picked_up_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ComboBasicRead(BaseModel):
    """Basic combo information for review responses"""

    id: str
    name: Optional[str] = None
    description: Optional[str] = None
    images: Optional[list] = None
    product_number: Optional[str] = None
    category: Optional[str] = None
    original_price: Optional[float] = None
    discount_percentage: float
    status: str

    model_config = {"from_attributes": True}


class ReviewRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    rating: int
    comment: Optional[str]
    created_at: datetime
    updated_at: datetime
    user_id: str
    shop_id: Optional[str]
    combo_id: Optional[str]
    order_id: Optional[str]
    locker_unit_id: Optional[str]


class ReviewDetailRead(BaseModel):
    """Enhanced review response with nested user, shop, locker, and order data"""

    model_config = {"from_attributes": True}

    id: str
    rating: int
    comment: Optional[str]
    created_at: datetime
    updated_at: datetime
    user: Optional[UserBasicRead] = None
    shop: Optional[ShopBasicRead] = None
    locker: Optional[LockerBasicRead] = None
    order: Optional[OrderBasicRead] = None
    combo: Optional[ComboBasicRead] = None
    locker_unit: Optional[LockerUnitRead] = None


class ReviewCreate(BaseModel):
    rating: int
    comment: str
    shop_id: Optional[str] = None
    combo_id: Optional[str] = None
    order_id: Optional[str] = None
    locker_unit_id: Optional[str] = None


class ReviewUpdate(BaseModel):
    rating: Optional[int] = None
    comment: Optional[str] = None
    shop_id: Optional[str] = None
    combo_id: Optional[str] = None
    order_id: Optional[str] = None
    locker_unit_id: Optional[str] = None
