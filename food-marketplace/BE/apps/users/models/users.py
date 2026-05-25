import uuid
from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel
from apps.core.utils import utcnow

from apps.core.config import IMAGE_USER_MALE


class UserRole(str, Enum):
    admin = "admin"
    customer = "customer"
    owner_shop = "owner_shop"
    owner_locker = "owner_locker"


class User(SQLModel, table=True):
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True,
        max_length=36,
    )
    username: Optional[str] = Field(index=True, max_length=150, nullable=True)
    password: str = Field(max_length=255)
    role: str = Field(default="customer", max_length=32, index=True)
    permissions: str = Field(default="customer", max_length=50)
    email: str = Field(index=True, max_length=255, nullable=False)
    birthday: Optional[date] = Field(default=None)
    gender: Optional[str] = Field(default=None, max_length=50)
    phone: Optional[str] = Field(default=None, max_length=20)
    name: Optional[str] = Field(default=None, max_length=200)
    first_name: Optional[str] = Field(default=None, max_length=100)
    last_name: Optional[str] = Field(default=None, max_length=100)
    address: Optional[str] = Field(default=None, max_length=500)
    verification_code: Optional[str] = Field(default=None, max_length=32)
    is_verified_email: bool = Field(default=False, index=True)
    icon: Optional[str] = Field(default=IMAGE_USER_MALE, max_length=1000)
    code_shop: Optional[str] = Field(default=None, max_length=15)
    shop_id: Optional[str] = Field(default=None, max_length=36, index=True, foreign_key="shop.id")
    my_portal: Optional[str] = Field(default="not linked", max_length=32)
    is_verification_qrcode: bool = Field(default=False, index=True)
    qrcode_verified_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    is_active: bool = Field(default=True, nullable=True)

    # Relationships
    owned_shop: Optional["Shop"] = Relationship(back_populates="owner", sa_relationship_kwargs={"foreign_keys": "Shop.owner_id"})  # type: ignore
    shop: Optional["Shop"] = Relationship(back_populates="staff_members", sa_relationship_kwargs={"foreign_keys": "User.shop_id"})  # type: ignore
    owned_locker_locations: List["LockerLocation"] = Relationship(back_populates="owner")  # type: ignore
    favorite_lockers: List["FavoriteLocker"] = Relationship(back_populates="user")  # type: ignore
    favorites: List["Favorite"] = Relationship(back_populates="user")  # type: ignore
