from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, field_validator

from apps.core.schemas import PositionParserMixin
from apps.orders.schemas import OrderRead
from apps.products.models import Combo


class ShopBasicRead(BaseModel):
    """Basic shop information for combo responses"""

    id: str
    name: Optional[str] = None
    description: Optional[str] = None
    avg_rating: float
    total_reviews: int
    is_favorite: bool = False  # This will be calculated based on user context

    model_config = {"from_attributes": True}


class ShopMinimalRead(BaseModel):
    """Minimal shop information for combo public responses"""

    id: str
    name: Optional[str] = None

    model_config = {"from_attributes": True}


# ===== Locker Location Schema =====
class LockerLocationBasic(PositionParserMixin, BaseModel):
    """Basic locker location information for combo responses"""

    id: str
    name: str
    address: Optional[str] = None
    description: Optional[str] = None
    code: Optional[str] = None
    # position field is inherited from PositionParserMixin and will return GeoJSON format

    model_config = {"from_attributes": True}


class LockerUnitRead(BaseModel):
    """Locker unit information for combo responses"""

    id: str
    unit_number: str  # Required field for unit identification
    status: str  # Required field for unit status
    size: str  # Required field for unit size
    access_code: Optional[str] = None  # Access code for the unit
    location: Optional[LockerLocationBasic] = None  # Nested location object
    preparation_deadline: Optional[datetime] = None  # From locker reservation
    locker_reservation_id: Optional[str] = None  # ID of the locker reservation

    # QR code URL cached in DB at access_code creation time
    qr_code_url: Optional[str] = None
    # True while combo status is PREPARATION_TO_LOCKER (shop still placing items)
    is_qr_active: bool = False

    model_config = {"from_attributes": True}


class ComboProductCreate(BaseModel):
    product_master_id: str
    quantity: int = 1
    expiry_dates: Optional[List[datetime]] = None


class ComboProductRead(BaseModel):
    id: str
    product_master_id: str
    quantity: int = 1
    expiry_dates: Optional[List[datetime]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "arbitrary_types_allowed": True}

    @field_validator("expiry_dates", mode="before")
    @classmethod
    def validate_expiry_dates(cls, v):
        """Convert ISO strings back to datetime objects if needed"""
        if v is None:
            return v
        if isinstance(v, list):
            converted_dates = []
            for date in v:
                if isinstance(date, str):
                    try:
                        converted_dates.append(
                            datetime.fromisoformat(date.replace("Z", "+00:00"))
                        )
                    except ValueError:
                        converted_dates.append(date)
                else:
                    converted_dates.append(date)
            return converted_dates
        return v


class ComboProductWithMasterRead(BaseModel):
    id: str
    product_master_id: str
    quantity: int = 1
    expiry_dates: Optional[List[datetime]] = None
    created_at: datetime
    updated_at: datetime
    product_master: "ProductMasterRead"

    model_config = {"from_attributes": True}

    @field_validator("expiry_dates", mode="before")
    @classmethod
    def validate_expiry_dates(cls, v):
        """Convert ISO strings back to datetime objects if needed"""
        if v is None:
            return v
        if isinstance(v, list):
            converted_dates = []
            for date in v:
                if isinstance(date, str):
                    try:
                        converted_dates.append(
                            datetime.fromisoformat(date.replace("Z", "+00:00"))
                        )
                    except ValueError:
                        converted_dates.append(date)
                else:
                    converted_dates.append(date)
            return converted_dates
        return v


class ComboCreate(BaseModel):
    shop_id: str
    products: List[ComboProductCreate]
    locker_unit_id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    images: Optional[List[str]] = None
    is_available: Optional[bool] = True
    discount_percentage: float = 0
    category: Optional[str] = None
    listing_end_date: Optional[datetime] = None
    pickup_deadline: Optional[datetime] = None
    sales_duration: Optional[str] = None
    is_free: Optional[bool] = False
    is_checked: Optional[bool] = False
    is_draft: Optional[bool] = False
    # combo_id for upgrade from draft in apps
    combo_id: Optional[str] = None
    # Note: original_price and product_number are auto-calculated/generated

    model_config = {
        "json_schema_extra": {
            "example": {
                "shop_id": "032ec926-7f08-40b4-8d91-9fbbb6fdd1fe",
                "locker_unit_id": "b2082868-e462-446a-8bff-3803d3a593a9",
                "products": [
                    {
                        "product_master_id": "8c05c0cb-8f5c-4228-98b3-fcb2d2233c67",
                        "quantity": 2,
                        "expiry_dates": ["2025-09-22T18:00:00", "2025-09-25T18:00:00"],
                    },
                    {
                        "product_master_id": "d1c0ee24-98eb-4cb1-b7ef-7d45406915e5",
                        "quantity": 1,
                        "expiry_dates": ["2025-09-26T18:00:00"],
                    },
                ],
                "name": "Lunch combo special",
                "description": "Fresh lunch combo with multiple items",
                "discount_percentage": 10.0,
                "category": "lunch",
                "listing_end_date": "2025-09-30T18:00:00",
                "pickup_deadline": "2025-09-30T20:00:00",
                "sales_duration": "2時間",
                "is_free": False,
                "is_draft": False,
                "is_checked": True,
            }
        }
    }


class ComboDraftCreate(BaseModel):
    """Schema for creating combo drafts - more flexible validation"""

    shop_id: str
    products: Optional[List[ComboProductCreate]] = []  # Optional for drafts
    locker_unit_id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    images: Optional[List[str]] = None
    is_available: Optional[bool] = True
    discount_percentage: float = 0
    category: Optional[str] = None
    listing_end_date: Optional[datetime] = None
    pickup_deadline: Optional[datetime] = None
    sales_duration: Optional[str] = None
    is_free: Optional[bool] = False
    is_checked: Optional[bool] = False
    # is_draft is always True for this schema

    model_config = {
        "json_schema_extra": {
            "example": {
                "shop_id": "032ec926-7f08-40b4-8d91-9fbbb6fdd1fe",
                "locker_unit_id": "b2082868-e462-446a-8bff-3803d3a593a9",
                "products": [
                    {
                        "product_master_id": "8c05c0cb-8f5c-4228-98b3-fcb2d2233c67",
                        "quantity": 2,
                        "expiry_dates": ["2025-09-22T18:00:00", "2025-09-25T18:00:00"],
                    },
                    {
                        "product_master_id": "d1c0ee24-98eb-4cb1-b7ef-7d45406915e5",
                        "quantity": 1,
                        "expiry_dates": ["2025-09-26T18:00:00"],
                    },
                ],
                "name": "Lunch combo special",
                "description": "Fresh lunch combo with multiple items",
                "discount_percentage": 10.0,
                "category": "lunch",
                "listing_end_date": "2025-09-30T18:00:00",
                "pickup_deadline": "2025-09-30T20:00:00",
                "sales_duration": "1時間30分",
                "is_free": True,
                "is_draft": False,
                "is_checked": True,
            }
        }
    }


class ComboRead(BaseModel):
    id: str
    shop_id: str
    name: str
    description: Optional[str] = None
    images: Optional[List[str]] = None
    is_available: bool = True
    original_price: Optional[float] = None
    discount_percentage: float = 0
    product_number: Optional[str] = None
    category: Optional[str] = None
    listing_end_date: Optional[datetime] = None
    pickup_deadline: Optional[datetime] = None
    sales_duration: Optional[str] = None
    is_free: bool = False
    is_draft: bool = False
    is_checked: bool = False
    status: str
    created_at: datetime
    updated_at: datetime
    edited_at: Optional[datetime] = None

    # Additional fields for public combo API (same as ComboListRead)
    shop: Optional[ShopMinimalRead] = None
    locker_unit: Optional[LockerUnitRead] = None
    distance: Optional[float] = 10.0  # Distance in km, None if not calculated

    # Countdown timer fields for app processing
    time_remaining_seconds: Optional[int] = None  # Total seconds until listing_end_date
    expires_at: Optional[datetime] = (
        None  # Exact expiration time (same as listing_end_date)
    )
    next_status_change_at: Optional[datetime] = None  # When status will change next

    # Discount logic fields for app to determine pricing
    can_be_free: Optional[bool] = (
        None  # True if combo has is_free=True (for MyNa Portal users)
    )
    current_effective_price: Optional[float] = None  # Actual price user will pay now
    discounted_price: Optional[float] = None  # Price after discount_percentage applied

    # Include the products in the combo
    combo_products: List[ComboProductRead] = []

    model_config = {"from_attributes": True}


class ComboListRead(BaseModel):
    """Schema for combo list responses without combo_products field"""

    id: str
    shop_id: str
    name: str
    description: Optional[str] = None
    images: Optional[List[str]] = None
    is_available: bool = True
    original_price: Optional[float] = None
    discount_percentage: float = 0
    product_number: Optional[str] = None
    category: Optional[str] = None
    listing_end_date: Optional[datetime] = None
    pickup_deadline: Optional[datetime] = None
    sales_duration: Optional[str] = None
    is_free: bool = False
    is_draft: bool = False
    is_checked: bool = False
    status: str
    created_at: datetime
    updated_at: datetime
    edited_at: Optional[datetime] = None

    # Additional fields for public combo API
    shop: Optional[ShopMinimalRead] = None
    locker_unit: Optional[LockerUnitRead] = None
    distance: Optional[float] = None  # Distance in km, None if not calculated

    # Countdown timer fields for app processing
    time_remaining_seconds: Optional[int] = None  # Total seconds until listing_end_date
    next_status_change_at: Optional[datetime] = None  # When status will change next

    # Discount logic fields for app to determine pricing
    can_be_free: Optional[bool] = (
        None  # True if combo has is_free=True (for MyNa Portal users)
    )
    current_effective_price: Optional[float] = None  # Actual price user will pay now
    discounted_price: Optional[float] = None  # Price after discount_percentage applied

    # Food loss and CO2 impact fields
    foodloss: Optional[float] = None  # Total food waste weight in kg
    co2_reduction: Optional[float] = None  # CO2 reduction in kg (foodloss * 2.5)

    model_config = {"from_attributes": True}


class ProductDetailPreview(BaseModel):
    """Product detail schema for combo preview with quantity and expiry dates"""

    # Product master fields
    id: str
    shop_id: str
    name: str
    description: Optional[str] = None
    selling_price: float
    food_waste_weight: Optional[float] = None
    storage_method: Optional[str] = None
    ingredients: Optional[str] = None
    additives: Optional[str] = None
    nutrition_facts: Optional[str] = None
    allergens: Optional[str] = None
    content_details: Optional[str] = None
    expiration_date_type: Optional[str] = None
    business_name: Optional[str] = None
    supplier_code: Optional[str] = None
    address_zip_code: Optional[str] = None
    address_prefecture: Optional[str] = None
    address_city: Optional[str] = None
    address_prefecture_id: Optional[str] = None
    address_city_id: Optional[str] = None
    address_street: Optional[str] = None
    images: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool = True

    # Combo-specific fields
    quantity: int = 1
    expiry_dates: Optional[List[datetime]] = None

    model_config = {"from_attributes": True}


class ComboPreview(BaseModel):
    """Preview schema for combo before creation - shows calculated values"""

    name: Optional[str] = None
    description: Optional[str] = None
    images: Optional[List[str]] = None
    is_available: bool = True
    original_price: float
    discount_percentage: float = 0
    final_price: float  # calculated price after discount
    category: Optional[str] = None
    listing_end_date: Optional[datetime] = None
    pickup_deadline: Optional[datetime] = None
    sales_duration: Optional[str] = None
    is_free: bool = False
    is_draft: bool = False
    is_checked: bool = False
    # Shop information
    shop: Optional[ShopBasicRead] = None
    # Locker information
    locker_unit: Optional[LockerUnitRead] = None
    # Product details for preview
    product_details: List["ProductDetailPreview"] = []
    total_products: int

    @field_validator("is_free", mode="before")
    @classmethod
    def validate_is_free(cls, v):
        """Handle None values for is_free field"""
        if v is None:
            return False
        return v

    @field_validator("sales_duration", mode="before")
    @classmethod
    def validate_sales_duration(cls, v):
        """Handle None values for sales_duration field"""
        if v is None:
            return None
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Special Bento Combo",
                "description": "A delicious combo deal featuring multiple premium products",
                "images": [
                    "https://example.com/combo-image1.jpg",
                    "https://example.com/combo-image2.jpg",
                ],
                "is_available": True,
                "original_price": 1500.0,
                "discount_percentage": 20.0,
                "final_price": 1200.0,
                "category": "Lunch Combo",
                "listing_end_date": "2025-09-22T15:00:00",
                "pickup_deadline": "2025-09-22T17:00:00",
                "sales_duration": "2時間",
                "is_free": False,
                "is_draft": False,
                "is_checked": False,
                "shop": {
                    "id": "032ec926-7f08-40b4-8d91-9fbbb6fdd1fe",
                    "name": "Wakeatte Kitchen",
                    "description": "Premium Japanese cuisine with fresh ingredients",
                    "avg_rating": 4.5,
                    "total_reviews": 128,
                    "is_favorite": False,
                },
                "locker_unit": {
                    "id": "b2082868-e462-446a-8bff-3803d3a593a9",
                    "location_name": "Shibuya Station East Exit",
                },
                "product_details": [
                    {
                        "id": "b5f079b6-cef6-41c3-8512-5b451a5478ab",
                        "shop_id": "d7923d0f-2291-472b-81d4-930f48a94829",
                        "name": "Premium Bento Box",
                        "description": "Delicious traditional Japanese bento with seasonal ingredients",
                        "selling_price": 1200,
                        "food_waste_weight": 0.5,
                        "storage_method": "冷蔵",
                        "ingredients": "Rice, chicken, vegetables, pickles, miso soup",
                        "allergens": "Soy, wheat, egg",
                        "images": ["https://example.com/bento-image.jpg"],
                        "created_at": "2025-09-20T04:26:09.798874",
                        "updated_at": "2025-09-20T04:26:09.798892",
                        "is_active": True,
                        "quantity": 2,
                        "expiry_dates": ["2025-09-22T18:00:00", "2025-09-25T18:00:00"],
                    }
                ],
                "total_products": 3,
            }
        }
    }


class ComboUpdate(BaseModel):
    shop_id: Optional[str] = None
    products: Optional[List[ComboProductCreate]] = None  # Allow updating products
    name: Optional[str] = None
    description: Optional[str] = None
    images: Optional[List[str]] = None
    is_available: Optional[bool] = None
    original_price: Optional[float] = None
    discount_percentage: Optional[float] = None
    product_number: Optional[str] = None
    category: Optional[str] = None
    listing_end_date: Optional[datetime] = None
    pickup_deadline: Optional[datetime] = None
    sales_duration: Optional[str] = None
    is_free: Optional[bool] = None
    is_checked: Optional[bool] = None
    is_draft: Optional[bool] = None
    status: Optional[str] = None

    # for case upgrade from draft
    locker_unit_id: Optional[str] = None

    model_config = {"from_attributes": True}


class ComboEdit(BaseModel):
    """Schema for editing combo information - simplified version"""

    images: Optional[List[str]] = None
    name: Optional[str] = None
    description: Optional[str] = None
    is_free: Optional[bool] = None
    discount_percentage: Optional[float] = None
    products: Optional[List[ComboProductCreate]] = None
    locker_unit_id: Optional[str] = None
    sales_duration: Optional[str] = None

    @field_validator("sales_duration")
    @classmethod
    def validate_sales_duration(cls, v):
        """Validate sales_duration is in SALES_DURATION_CHOICES"""
        if v is not None and v not in Combo.SALES_DURATION_CHOICES:
            raise ValueError(
                f"sales_duration must be one of {Combo.SALES_DURATION_CHOICES}"
            )
        return v

    model_config = {"from_attributes": True}


class ProductMasterCreate(BaseModel):
    shop_id: str
    name: str
    description: Optional[str] = None
    selling_price: float
    food_waste_weight: Optional[float] = None
    storage_method: Optional[str] = None
    ingredients: Optional[str] = None
    additives: Optional[str] = None
    nutrition_facts: Optional[str] = None
    allergens: Optional[str] = None
    content_details: Optional[str] = None
    expiration_date_type: Optional[str] = None
    business_name: Optional[str] = None
    supplier_code: Optional[str] = None
    address_zip_code: Optional[str] = None
    address_prefecture: Optional[str] = None
    address_city: Optional[str] = None
    address_prefecture_id: Optional[str] = None
    address_city_id: Optional[str] = None
    address_street: Optional[str] = None
    address_block: Optional[str] = None
    apartment_name: Optional[str] = None
    images: Optional[List[str]] = None
    is_active: bool = True

    model_config = {
        "json_schema_extra": {
            "example": {
                "address_city": "Chiyoda",
                "address_prefecture": "Tokyo",
                "address_street": "1-1-1 Marunouchi",
                "address_prefecture_id": "str",
                "address_city_id": "str",
                "address_zip_code": "100-0001",
                "allergens": "Soy, wheat, egg",
                "business_name": "Wakeatte Kitchen",
                "content_details": "Main dish: Teriyaki chicken, Side: Seasonal vegetables, Rice: Japanese short grain",
                "description": "Delicious traditional Japanese bento with seasonal ingredients",
                "expiration_date_type": "製造日から3日",
                "food_waste_weight": 0.5,
                "images": ["https://example.com/bento-image.jpg"],
                "ingredients": "Rice, chicken, vegetables, pickles, miso soup",
                "additives": "Preservatives, colorings, flavor enhancers",
                "nutrition_facts": "Energy: 450kcal, Protein: 25g, Fat: 12g, Carbs: 60g",
                "is_active": True,
                "name": "Premium Bento Box",
                "selling_price": 1200,
                "shop_id": "550e8400-e29b-41d4-a716-446655440000",
                "storage_method": "冷蔵",
                "supplier_code": "SUP001",
            }
        }
    }


class ProductMasterRead(BaseModel):
    id: str
    shop_id: str
    name: str
    description: Optional[str] = None
    selling_price: float
    food_waste_weight: Optional[float] = None
    storage_method: Optional[str] = None
    ingredients: Optional[str] = None
    additives: Optional[str] = None
    nutrition_facts: Optional[str] = None
    allergens: Optional[str] = None
    content_details: Optional[str] = None
    expiration_date_type: Optional[str] = None
    business_name: Optional[str] = None
    supplier_code: Optional[str] = None
    address_zip_code: Optional[str] = None
    address_prefecture: Optional[str] = None
    address_city: Optional[str] = None
    address_prefecture_id: Optional[str] = None
    address_city_id: Optional[str] = None
    address_street: Optional[str] = None
    address_block: Optional[str] = None
    apartment_name: Optional[str] = None

    images: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": 200,
                "message": "successful",
                "data": {
                    "id": "a4f19cc5-6259-4373-a4f6-ef2611718289",
                    "shop_id": "44eb714f-97ea-4082-8112-49d00559dfcd",
                    "name": "Premium Bento Box",
                    "description": "Delicious traditional Japanese bento with seasonal ingredients",
                    "selling_price": 1300,
                    "food_waste_weight": 0.5,
                    "storage_method": "冷蔵",
                    "ingredients": "Rice, chicken, vegetables, pickles, miso soup",
                    "allergens": "Soy, wheat, egg",
                    "content_details": "Main dish: Teriyaki chicken, Side: Seasonal vegetables, Rice: Japanese short grain",
                    "expiration_date_type": "製造日から3日",
                    "business_name": "Wakeatte Kitchen",
                    "supplier_code": "SUP001",
                    "address_zip_code": "100-0001",
                    "address_prefecture": "Tokyo",
                    "address_city": "Chiyoda",
                    "address_prefecture_id": "str",
                    "address_city_id": "str",
                    "address_street": "1-1-1 Marunouchi",
                    "address_block": "str",
                    "apartment_name": "str",
                    "images": "[https://example.com/bento-image.jpg]",
                    "created_at": "2025-09-19T06:44:07.723148",
                    "updated_at": "2025-09-19T06:44:07.723177",
                    "is_active": True,
                },
            }
        }
    }


class ComboProductFlattened(ProductMasterRead):
    """Flattened combo product with product master info at the same level"""

    # Combo Product fields - these will be added to all ProductMasterRead fields
    quantity: int = 1
    expiry_dates: Optional[List[datetime]] = None

    model_config = {"from_attributes": True}

    @field_validator("expiry_dates", mode="before")
    @classmethod
    def validate_expiry_dates(cls, v):
        """Convert ISO strings back to datetime objects if needed"""
        if v is None:
            return v
        if isinstance(v, list):
            converted_dates = []
            for date in v:
                if isinstance(date, str):
                    # Parse ISO format string back to datetime
                    try:
                        converted_dates.append(
                            datetime.fromisoformat(date.replace("Z", "+00:00"))
                        )
                    except ValueError:
                        # If parsing fails, keep as string
                        converted_dates.append(date)
                else:
                    converted_dates.append(date)
            return converted_dates
        return v

    @classmethod
    def from_combo_product(cls, combo_product) -> "ComboProductFlattened":
        """Create flattened product from combo_product with product_master"""
        if not combo_product.product_master:
            raise ValueError("ComboProduct must have product_master loaded")

        # Start with product master data
        product_data = combo_product.product_master.__dict__.copy()
        product_data.pop("_sa_instance_state", None)  # Remove SQLAlchemy internals

        # Ensure shop_id is present (from combo_product or product_master)
        if hasattr(combo_product, "shop_id") and combo_product.shop_id:
            product_data["shop_id"] = combo_product.shop_id
        elif (
            hasattr(combo_product.product_master, "shop_id")
            and combo_product.product_master.shop_id
        ):
            product_data["shop_id"] = combo_product.product_master.shop_id

        # Add combo product specific fields
        product_data.update(
            {
                "quantity": combo_product.quantity,
                "expiry_dates": combo_product.expiry_dates,
            }
        )

        return cls.model_validate(product_data)


class LockerUnitBasic(BaseModel):
    """Basic locker unit information for combo responses"""

    id: str
    unit_number: str
    status: str
    size: str
    location: Optional[LockerLocationBasic] = None

    model_config = {"from_attributes": True}


class ComboFlattenedRead(BaseModel):
    """Combo response with flattened product information and shop details"""

    id: str
    shop_id: str
    name: str
    description: Optional[str] = None
    images: Optional[List[str]] = None
    is_available: bool = True
    original_price: Optional[float] = None
    discount_percentage: float = 0
    product_number: Optional[str] = None
    category: Optional[str] = None
    listing_end_date: Optional[datetime] = None
    pickup_deadline: Optional[datetime] = None
    sales_duration: Optional[str] = None
    is_free: bool = False
    is_draft: bool = False
    is_checked: bool = False
    status: str
    created_at: datetime
    updated_at: datetime
    edited_at: Optional[datetime] = None

    # Additional fields for public combo API (same as ComboRead)
    # Shop information
    shop: Optional[ShopBasicRead] = None
    # Flattened products list
    products: List[ComboProductFlattened] = []
    # Locker information
    locker_unit: Optional[LockerUnitRead] = None
    # Order Information
    order: Optional[OrderRead] = None
    distance: Optional[float] = 10.0  # Distance in km, None if not calculated

    # Countdown timer fields for app processing
    time_remaining_seconds: Optional[int] = None  # Total seconds until listing_end_date
    next_status_change_at: Optional[datetime] = None  # When status will change next

    # Discount logic fields for app to determine pricing
    can_be_free: Optional[bool] = (
        None  # True if combo has is_free=True (for MyNa Portal users)
    )
    current_effective_price: Optional[float] = None  # Actual price user will pay now
    discounted_price: Optional[float] = None  # Price after discount_percentage applied

    # Food loss and CO2 impact fields
    foodloss: Optional[float] = None  # Total food waste weight in kg (sum of food_waste_weight * quantity / 1000)
    co2_reduction: Optional[float] = None  # CO2 reduction in kg (foodloss * 2.5)

    model_config = {"from_attributes": True}

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        # If input dict has 'combo_products' but not 'products', map it for backward compatibility
        if isinstance(obj, dict):
            if "combo_products" in obj and "products" not in obj:
                obj = obj.copy()
                obj["products"] = obj["combo_products"]
            # Remove combo_products from input to avoid conflicts
            elif "products" in obj and "combo_products" in obj:
                obj = obj.copy()
                obj.pop("combo_products", None)
        return super().model_validate(obj, *args, **kwargs)


class ProductMasterUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    selling_price: Optional[float] = None
    food_waste_weight: Optional[float] = None
    storage_method: Optional[str] = None
    ingredients: Optional[str] = None
    additives: Optional[str] = None
    nutrition_facts: Optional[str] = None
    allergens: Optional[str] = None
    content_details: Optional[str] = None
    expiration_date_type: Optional[str] = None
    business_name: Optional[str] = None
    supplier_code: Optional[str] = None
    address_zip_code: Optional[str] = None
    address_prefecture: Optional[str] = None
    address_city: Optional[str] = None
    address_prefecture_id: Optional[str] = None
    address_city_id: Optional[str] = None
    address_street: Optional[str] = None
    address_block: Optional[str] = None
    apartment_name: Optional[str] = None
    images: Optional[List[str]] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "address_city": "Chiyoda",
                "address_prefecture": "Tokyo",
                "address_prefecture_id": "str",
                "address_city_id": "str",
                "address_street": "1-1-1 Marunouchi",
                "address_zip_code": "100-0001",
                "address_block": "str",
                "apartment_name": "str",
                "allergens": "Soy, wheat, egg",
                "business_name": "Wakeatte Kitchen",
                "content_details": "Main dish: Teriyaki chicken, Side: Seasonal vegetables, Rice: Japanese short grain",
                "description": "Delicious traditional Japanese bento with seasonal ingredients",
                "expiration_date_type": "製造日から3日",
                "food_waste_weight": 0.5,
                "images": "[https://example.com/bento-image.jpg]",
                "ingredients": "Rice, chicken, vegetables, pickles, miso soup",
                "additives": "Preservatives, colorings, flavor enhancers",
                "nutrition_facts": "Energy: 450kcal, Protein: 25g, Fat: 12g, Carbs: 60g",
                "name": "Premium Bento Box",
                "selling_price": 1200,
                "storage_method": "冷蔵",
                "supplier_code": "SUP001",
            }
        }
    }
