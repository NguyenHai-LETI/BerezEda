"""
Order API Schemas
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr

from apps.core.schemas import PositionParserMixin


class OrderCreate(BaseModel):
    combo_id: str
    edited_at: Optional[datetime] = None
    card_id: Optional[str] = None
    payment_method: Optional[str] = "card"
    notes: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "combo_id": "combo-12345",
                "edited_at": "2025-11-06 10:50:53.309129",
                "card_id": "cs_AmyuxPdCRX-Qg8T4wRPbCA",
                "payment_method": "card",
                "notes": "Please prepare quickly",
            }
        }
    }


class OrderUserRead(BaseModel):
    id: Optional[str] = None
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    model_config = {"from_attributes": True}


class OrderRead(BaseModel):
    id: str
    user_id: str
    combo_id: str
    shop_id: str
    order_number: str
    status: str
    original_price: float
    discount_percentage: float
    final_price: float
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    pickup_code: Optional[str] = None
    pickup_deadline: Optional[datetime] = None
    picked_up_at: Optional[datetime] = None
    payment_method: Optional[str] = None
    # payment_status: Optional[str] = None
    transaction_id: Optional[str] = None
    notes: Optional[str] = None
    is_review: bool = False

    combo_name: Optional[str] = None
    combo_images: Optional[List[str]] = None
    user: Optional[OrderUserRead] = None

    model_config = {"from_attributes": True}

    @classmethod
    def build(cls, order_obj, combo_obj=None, user_obj=None):
        order_dict = order_obj.__dict__.copy()
        order_dict.pop("_sa_instance_state", None)

        combo = combo_obj or getattr(order_obj, "combo", None)
        if combo:
            order_dict["combo_name"] = combo.name
            order_dict["combo_images"] = combo.images

        order_dict["is_review"] = bool(getattr(order_obj, "is_review", False))

        user = user_obj or getattr(order_obj, "user", None)
        if user:
            order_dict["user"] = OrderUserRead.model_validate(
                user, from_attributes=True
            )

        return cls.model_validate(order_dict)


class ShopDataRead(BaseModel):
    """Shop information for order details"""

    id: str
    name: Optional[str] = None

    model_config = {"from_attributes": True}


class ComboDataRead(BaseModel):
    """Combo information for order details"""

    id: str
    name: str
    product_number: Optional[str] = None
    images: Optional[List[str]] = None

    model_config = {"from_attributes": True}


class LockerDataRead(PositionParserMixin):
    """Locker information for order details"""

    id: str
    name: str  # This will be the location name
    unit_number: Optional[str] = None

    model_config = {"from_attributes": True}


class OrderDetailRead(BaseModel):
    """Enhanced order details with related objects"""

    id: str
    user_id: str
    order_number: str
    status: str
    original_price: float
    discount_percentage: float
    final_price: float
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    pickup_code: Optional[str] = None
    pickup_deadline: Optional[datetime] = None
    picked_up_at: Optional[datetime] = None
    payment_method: Optional[str] = None
    # payment_status: Optional[str] = None
    transaction_id: Optional[str] = None
    notes: Optional[str] = None
    locker_unit_id: Optional[str] = None
    is_review: bool = False

    # Enhanced objects
    shop: Optional[ShopDataRead] = None
    combo: Optional[ComboDataRead] = None
    locker: Optional[LockerDataRead] = None
    qr_code_url: Optional[str] = None
    # True while order status is READY_FOR_PICKUP (user can still use the QR to collect)
    is_qr_active: bool = False

    model_config = {"from_attributes": True}


class OrderWithComboDetails(BaseModel):
    """Order with combo information for customer display"""

    id: str
    order_number: str
    status: str
    final_price: float
    created_at: datetime
    pickup_code: Optional[str] = None
    pickup_deadline: Optional[datetime] = None

    # Combo details
    combo_name: str
    combo_description: Optional[str] = None
    combo_images: Optional[list[str]] = None
    shop_name: str
    shop_id: str

    # Pickup location info (from locker)
    locker_location: Optional[str] = None
    locker_address: Optional[str] = None

    model_config = {"from_attributes": True}


class OrderStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None
