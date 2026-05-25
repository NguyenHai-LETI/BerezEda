import uuid
from datetime import datetime, timezone
from typing import ClassVar, List, Optional

from sqlmodel import JSON, Column, Field, Relationship, SQLModel


class ProductMaster(SQLModel, table=True):
    __tablename__: ClassVar[str] = "product_masters"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True,
        max_length=36,
    )
    shop_id: str = Field(foreign_key="shop.id", max_length=36, index=True)
    name: str = Field(max_length=255)
    description: Optional[str] = Field(default=None)
    selling_price: float = Field()
    food_waste_weight: Optional[float] = Field(default=None)
    storage_method: Optional[str] = Field(default=None, max_length=500)
    ingredients: Optional[str] = Field(
        default=None, description="原材料名 - Ingredients", max_length=500
    )
    additives: Optional[str] = Field(
        default=None, description="添加物 - Additives", max_length=500
    )
    nutrition_facts: Optional[str] = Field(
        default=None,
        description="栄養成分の量及び熱量 - Nutrition facts & calories",
        max_length=500,
    )
    allergens: Optional[str] = Field(default=None)
    content_details: Optional[str] = Field(
        default=None, description="内容量または固形量および内容総量", max_length=500
    )
    expiration_date_type: Optional[str] = Field(default=None, max_length=50)
    business_name: Optional[str] = Field(default=None, max_length=500)
    supplier_code: Optional[str] = Field(default=None, max_length=50)
    address_zip_code: Optional[str] = Field(default=None, max_length=10)
    address_prefecture: Optional[str] = Field(default=None, max_length=100)
    address_city: Optional[str] = Field(default=None, max_length=100)
    address_prefecture_id: Optional[str] = Field(default=None, max_length=50)
    address_city_id: Optional[str] = Field(default=None, max_length=50)
    address_street: Optional[str] = Field(default=None, max_length=255)
    address_block: Optional[str] = Field(default=None, max_length=255)
    apartment_name: Optional[str] = Field(default=None, max_length=255)
    images: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = Field(default=True)

    shop: Optional["Shop"] = Relationship(back_populates="products_master")  # type: ignore
    combo_products: List["ComboProduct"] = Relationship(back_populates="product_master")  # type: ignore
