from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, field_validator

from apps.core.constants import UNIT_SIZE_CHOICES
from apps.core.schemas import PositionParserMixin


# ===== Shop Schema for Locker Locations =====
class ShopMinimalRead(BaseModel):
    """Minimal shop information for locker location responses"""

    id: str
    name: Optional[str] = None

    model_config = {"from_attributes": True}


# ===== LockerLocation Schemas =====
class LockerLocationBase(BaseModel):
    name: str
    code: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool = True


class LockerLocationCreate(LockerLocationBase):
    image: Optional[str] = None
    position: Optional[str] = None
    shop_ids: Optional[List[str]] = (
        None  # List of shop IDs to associate with this location
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Tokyo Station East Exit",
                "code": "TKY_EAST_001",
                "image": "https://example.com/bento-image.jpg",
                "address": "1-9-1 Marunouchi, Chiyoda City, Tokyo 100-0005",
                "description": "Convenient locker location near Tokyo Station East Exit for travelers",
                "phone": "03-1234-5678",
                "position": "35.6812,139.7671",  # Input as string
                "is_active": True,
                "shop_ids": ["shop-id-1", "shop-id-2"],
            }
        }
    }


class LockerLocationUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    image: Optional[str] = None
    description: Optional[str] = None
    phone: Optional[str] = None
    position: Optional[str] = None  # Accept string input for update
    is_active: Optional[bool] = None
    shop_ids: Optional[List[str]] = (
        None  # List of shop IDs to associate with this location
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Locker Shibuya Station",
                "address": "2-24-12 Shibuya, Tokyo, Japan",
                "image": "https://example.com/images/locker_shibuya.jpg",
                "position": "35.6595,139.7005",
                "description": "Main locker area near Hachiko exit.",
                "phone": "+81-3-1234-5678",
                "is_active": True,
                "shop_ids": [
                    "c8f64a32-7b7d-48a1-9b38-bc12e9238a7f",
                    "a9d12e53-2b49-47e1-8121-4b6f920ad88e",
                ],
            }
        }
    }


class LockerLocationPublicRead(PositionParserMixin, LockerLocationBase):
    id: str
    distance: Optional[float] = None
    image: Optional[str] = None
    # TODO: caculate number of combos in the locker
    number_combos: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    is_favorite: bool = False
    favorite_sort_order: Optional[int] = None

    model_config = {"from_attributes": True}


class LockerLocationRead(PositionParserMixin, LockerLocationBase):
    id: str
    shops: List[ShopMinimalRead] = []  # List of associated shops with id and name
    image: Optional[str] = None
    distance: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LockerLocationWithUnits(LockerLocationRead):
    units: List["LockerUnitRead"] = []
    number_of_columns: Optional[int] = None
    foodloss: Optional[float] = None  # Total food waste in kg from orders today (JST)
    co2_reduction: Optional[float] = None  # CO2 reduction in kg (foodloss * 2.5)

    model_config = {"from_attributes": True}


# ===== Favorite Locker (My Locker) Schemas =====
class FavoriteLockerCreate(BaseModel):
    locker_location_id: str


class FavoriteLockerReorder(BaseModel):
    locker_location_ids: List[str]


class FavoriteLockerRead(BaseModel):
    """One favorite locker item with location details."""

    id: str
    locker_location_id: str
    sort_order: int
    favorited_at: datetime
    last_used_at: Optional[datetime] = None
    # Flattened location info (or reuse LockerLocationPublicRead)
    name: Optional[str] = None
    address: Optional[str] = None
    position: Optional[dict] = None
    image: Optional[str] = None
    distance: Optional[float] = None

    model_config = {"from_attributes": True}


class SyncFromGuestResponse(BaseModel):
    synced: bool
    title: Optional[str] = None
    message: Optional[str] = None


# ===== LockerUnit Schemas =====
class LockerUnitBase(BaseModel):
    location_id: str
    unit_number: str
    status: str = "available"
    size: str = "medium"
    is_active: bool = True


class LockerUnitCreate(LockerUnitBase):
    model_config = {
        "json_schema_extra": {
            "example": {
                "location_id": "aef1a9e5-8bdc-4b34-989c-dcf1c18b78b1",
                "unit_number": "A-001",
                "status": "available",
                "size": "medium",
                "is_active": True,
            }
        }
    }


class LockerUnitUpdate(BaseModel):
    location_id: Optional[str] = None
    unit_number: Optional[str] = None
    status: Optional[str] = None
    size: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("size")
    @classmethod
    def validate_size(cls, v):
        if v is not None and v not in UNIT_SIZE_CHOICES:
            raise ValueError(f"Size must be one of: {UNIT_SIZE_CHOICES}")
        return v


class LockerUnitRead(LockerUnitBase):
    id: str
    temperature: Optional[str] = None
    column_index: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LockerUnitWithLocation(LockerUnitRead):
    location: LockerLocationRead

    model_config = {"from_attributes": True}


class LockerUnitWithReservations(LockerUnitRead):
    reservations: List["LockerReservationRead"] = []

    model_config = {"from_attributes": True}


# ===== LockerReservation Schemas =====
class LockerReservationBase(BaseModel):
    locker_unit_id: str
    user_id: Optional[str] = None
    shop_id: str
    combo_id: Optional[str] = None
    notes: Optional[str] = None


class LockerReservationCreate(BaseModel):
    locker_unit_id: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "locker_unit_id": "0e7abcc2-e3f4-477d-bbfa-4678d229572f",
            }
        }
    }


class LockerReservationUpdate(BaseModel):
    locker_unit_id: Optional[str] = None
    combo_id: Optional[str] = None
    status: Optional[str] = None
    access_code: Optional[str] = None
    item_deposited_at: Optional[datetime] = None
    item_collected_at: Optional[datetime] = None
    notes: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v is not None:
            # Convert to uppercase for consistent storage
            v_upper = v.upper()
            allowed_statuses = ["ACTIVE", "COMPLETED", "CANCELLED"]
            if v_upper not in allowed_statuses:
                raise ValueError(
                    f"Status must be one of: {allowed_statuses} (case insensitive)"
                )
            return v_upper
        return v


class LockerReservationRead(BaseModel):
    id: str
    locker_unit_id: str
    user_id: Optional[str] = None
    shop_id: str
    combo_id: Optional[str] = None
    status: str
    access_code: Optional[str] = None
    item_deposited_at: Optional[datetime] = None
    item_collected_at: Optional[datetime] = None

    # Timing fields for combo placement and sale
    preparation_deadline: Optional[datetime] = None
    sale_end_time: Optional[datetime] = None
    price_reduction_time: Optional[datetime] = None

    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # QR code URL property - computed dynamically
    qr_code_url: Optional[str] = None

    # Location description from locker location
    description: Optional[str] = None  # From lockerlocation.description

    model_config = {"from_attributes": True}


class LockerReservationWithUnit(LockerReservationRead):
    unit: LockerUnitWithLocation

    model_config = {"from_attributes": True}


# ===== Special Action Schemas =====
class DepositItemRequest(BaseModel):
    reservation_id: str
    access_code: str


class CollectItemRequest(BaseModel):
    reservation_id: str
    access_code: str


class CheckAvailabilityRequest(BaseModel):
    location_id: str
    size: Optional[str] = None


class AvailableUnitResponse(BaseModel):
    unit_id: str
    unit_number: str
    size: str
    location_name: str
    estimated_price: float

    model_config = {"from_attributes": True}


# ===== List Response Schemas =====
class LockerLocationListResponse(BaseModel):
    locations: List[LockerLocationRead]
    total: int
    limit: int
    offset: int


# ===== Timing Information Schema =====
class ReservationTimingInfo(BaseModel):
    reservation_id: str
    timing_info: dict  # Contains human-readable time remaining info
    current_combo_status: Optional[str] = None
    preparation_deadline: Optional[datetime] = None
    sale_end_time: Optional[datetime] = None
    price_reduction_time: Optional[datetime] = None
    item_deposited_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ShopCooldownInfo(BaseModel):
    shop_id: str
    in_cooldown: bool
    can_reserve: bool
    message: Optional[str] = None
    cooldown_reason: Optional[str] = None
    failed_reservation_id: Optional[str] = None
    cooldown_start: Optional[datetime] = None
    remaining_time: Optional[str] = None
    cooldown_end: Optional[str] = None

    model_config = {"from_attributes": True}


# ===== LockerUnit Temperature Schemas =====
class LockerUnitSetTemperatureByColumn(BaseModel):
    column_index: int
    temperature: Optional[str] = None


# ===== CSV Import Schemas =====
class LockerUnitImportRequest(BaseModel):
    """Schema for CSV import request"""

    location_id: str
    # CSV file will be uploaded separately

    model_config = {
        "json_schema_extra": {
            "example": {
                "location_id": "123e4567-e89b-12d3-a456-426614174000",
            }
        }
    }


class LockerUnitImportResponse(BaseModel):
    """Schema for CSV import response"""

    success: bool
    imported_count: int
    skipped_count: int
    errors: List[str] = []
    imported_units: List[LockerUnitRead] = []

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "imported_count": 15,
                "skipped_count": 0,
                "errors": [],
                "imported_units": [],
            }
        }
    }


# Forward references
LockerLocationWithUnits.model_rebuild()
LockerUnitWithReservations.model_rebuild()
LockerReservationWithUnit.model_rebuild()


# ===== Search History Schemas =====
class SearchHistoryCreate(BaseModel):
    locker_location_id: str


class SearchHistoryRead(BaseModel):
    locker_location_id: str
    name: Optional[str] = None
    searched_at: datetime

    model_config = {"from_attributes": True}
