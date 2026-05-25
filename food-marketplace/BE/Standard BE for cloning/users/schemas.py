from datetime import date, datetime
from typing import Annotated, Dict, List, Optional

from pydantic import BaseModel, EmailStr, StringConstraints, model_validator

from apps.lockers.schemas import LockerLocationPublicRead
from apps.shops.schemas import ShopCreate, ShopRead, ShopUpdate


class CustomerCreate(BaseModel):
    """
    Customer registration schema.
    Public endpoint - only for customer registration.
    """

    first_name: str
    last_name: str
    gender: str
    birthday: Optional[date] = None
    address: str
    email: EmailStr
    phone: Optional[str] = None
    password: str
    username: Optional[str] = None
    role: str = "customer"

    model_config = {
        "json_schema_extra": {
            "example": {
                "first_name": "Customer",
                "last_name": "Name",
                "gender": "male",
                "birthday": "2025-09-15",
                "address": "Hà Nội Việt Nam",
                "email": "customer@example.com",
                "phone": "0123456789",
                "password": "Aa@12345678",
                "username": "customer_user",
                "role": "customer",
            }
        }
    }

    @model_validator(mode="after")
    def check_customer_fields(self):
        if self.role != "customer":
            raise ValueError("Public registration only allows customer role")
        if not self.email:
            raise ValueError("Email is required for customer registration")
        return self


class UserCreate(BaseModel):
    """
    ## User registration schema

    - Email is required for all user roles.
    - If role is not 'shop', the 'shop' field is ignored.
    - If role is 'customer', username is also required.
    """

    username: Optional[str] = None
    email: EmailStr
    phone: Optional[str] = None
    icon: Optional[str] = None
    first_name: str
    last_name: str
    gender: str
    birthday: Optional[date]
    address: Optional[str] = None
    password: str
    role: str
    permissions: Optional[list[str]] = None
    shop: Optional[ShopCreate] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "username": "tuanpx.na",
                "email": "tuanpx.it@gmail.com",
                "address": "Hà Nội Việt Nam",
                "phone": "0123456789",
                "first_name": "美味しい",
                "last_name": "もの",
                "gender": "male",
                "birthday": "2025-09-15",
                "password": "Aa@12345678",
                "role": "owner_shop",
                "shop": {
                    "name": "My Shop",
                    "address": "2-chōme-1-1 Hamachō, Funabashi, Chiba 273-8530",
                    "phone": "0909-999-123",
                    "logo": "https://example.com/logo.png",
                    "position": "35.694003,139.982047",
                },
            }
        }
    }

    @model_validator(mode="after")
    def check_fields(self):
        # Validate role is allowed
        allowed_roles = ["customer", "admin", "owner_locker", "owner_shop"]
        if self.role not in allowed_roles:
            raise ValueError(f"Role must be one of: {', '.join(allowed_roles)}")

        # Email is required for all roles
        if not self.email:
            raise ValueError("Email is required for all user registrations")

        # Shop-specific validation
        if self.role == "owner_shop":
            if not self.shop:
                raise ValueError("Shop information is required for shop users")
            if not self.shop.name or not self.shop.name.strip():
                raise ValueError("Shop name is required and cannot be empty")
            if not self.shop.address or not self.shop.address.strip():
                raise ValueError("Shop address is required and cannot be empty")

        # Permissions validation
        if self.permissions:
            valid_permissions = [
                "Administrator",
                "admin",
                "owner_locker",
                "owner_shop",
                "staff_shop",
                "customer",
            ]
            for permission in self.permissions:
                if permission not in valid_permissions:
                    raise ValueError(f"Invalid permission: {permission}")

        return self


class StaffCreate(BaseModel):
    email: EmailStr
    password: str
    phone: Optional[str] = None
    first_name: str
    last_name: str
    gender: Optional[str] = None
    birthday: date
    address: Optional[str] = None
    role: str = "owner_shop"
    permissions: str = "staff_shop"

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "staff@example.com",
                "password": "Aa@12345678",
                "address": "Hà Nội Việt Nam",
                "phone": "0123456789",
                "first_name": "Staff",
                "last_name": "Name",
                "gender": "male",
                "birthday": "2025-09-15",
                "role": "owner_shop",
                "permissions": "staff_shop",
            }
        }
    }

    @model_validator(mode="after")
    def check_staff_fields(self):
        if self.role != "owner_shop":
            raise ValueError("Shop staff only allows shop owner role")
        if self.permissions != "staff_shop":
            raise ValueError("Permissions only allows staff_shop")
        return self


class UserRead(BaseModel):
    id: str
    username: Optional[str] = None
    role: str
    permissions: Optional[str] = None
    email: EmailStr
    birthday: Optional[date] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    address: Optional[str] = None
    is_verified_email: bool
    icon: Optional[str] = None
    code_shop: Optional[str] = None
    other_attributes: Optional[Dict] = None
    my_portal: Optional[str] = None
    is_verification_qrcode: bool
    qrcode_verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    shops: Optional[ShopRead] = None
    lockers: Optional[List[LockerLocationPublicRead]] = None

    @classmethod
    def build_locker(cls, user_obj, locker_locations=None):
        """Build locker information for users with owner_locker role"""
        user_dict = user_obj.__dict__.copy()

        if locker_locations and len(locker_locations) > 0:
            # Convert list of LockerLocation objects to list of LockerLocationPublicRead
            locker_list = []
            for locker in locker_locations:
                locker_dict = locker.__dict__.copy()
                locker_dict.pop("_sa_instance_state", None)
                locker_list.append(LockerLocationPublicRead.model_validate(locker_dict))
            user_dict["lockers"] = locker_list
        else:
            user_dict["lockers"] = None

        # Set shops to None for locker owners
        user_dict["shops"] = None

        return cls.model_validate(user_dict)

    @classmethod
    def build(cls, user_obj, shop_obj=None):
        user_dict = user_obj.__dict__.copy()

        if hasattr(user_obj, "name"):
            user_dict["name"] = user_obj.name

        if shop_obj:
            shop_dict = shop_obj.__dict__.copy()
            shop_dict.pop("_sa_instance_state", None)
            user_dict["shops"] = ShopRead.model_validate(shop_dict)
        else:
            user_dict["shops"] = None
        return cls.model_validate(user_dict)

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "7798a986-7e59-4d68-8687-222dd635910e",
                "username": "null",
                "role": "owner_shop",
                "email": "tuanpx.it@gmail.com",
                "birthday": "2025-09-15",
                "gender": "male",
                "phone": "0123456789",
                "first_name": "美味しい",
                "last_name": "もの",
                "address": "Hà Nội Việt Nam",
                "is_verified_email": "false",
                "icon": "None/avatar_default/male.jpg",
                "code_shop": "666264",
                "other_attributes": "null",
                "my_portal": "not linked",
                "is_verification_qrcode": "false",
                "qrcode_verified_at": "null",
                "created_at": "2025-09-16T12:44:12.012223",
                "updated_at": "2025-09-16T12:44:12.012290",
                "shops": {
                    "id": "396a6818-e05e-48f0-aa32-2eb388323801",
                    "code": "666264",
                    "name": "My Shop",
                    "address": "2-chōme-1-1 Hamachō, Funabashi, Chiba 273-8530",
                    "phone": "0909-999-123",
                    "logo": "https://example.com/logo.png",
                    "is_active": "true",
                    "position": "35.694003,139.982047",
                    "avg_rating": 0,
                    "total_reviews": 0,
                    "created_at": "2025-09-16T12:44:12.399808",
                    "updated_at": "2025-09-16T12:44:12.400593",
                },
            },
        }
    }


class UserUpdate(BaseModel):
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[str] = None
    icon: Optional[str] = None
    birthday: Optional[date] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    shop: Optional[ShopCreate] = None
    password: Optional[Annotated[str, StringConstraints(min_length=8)]] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "tuanpx.it@gmail.com",
                "address": "Hà Nội Việt Nam",
                "phone": "0123456789",
                "icon": "string",
                "first_name": "美味しい",
                "last_name": "もの",
                "gender": "male",
                "birthday": "2025-09-15",
                "password": "Aa@12345678",
                "shop": {
                    "name": "My Shop",
                    "address": "2-chōme-1-1 Hamachō, Funabashi, Chiba 273-8530",
                    "phone": "0909-999-123",
                    "logo": "https://example.com/logo.png",
                    "position": "35.694003,139.982047",
                },
                "permissions": ["admin", "owner_shop"],
            }
        }
    }


class VerifyAndChangePasswordSchema(BaseModel):
    email: EmailStr
    verification_code: str
    new_password: Annotated[str, StringConstraints(min_length=8)]


class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    model_config = {"json_schema_extra": {"example": {"email": "user@example.com"}}}


class ResetPasswordRequest(BaseModel):
    password: Annotated[str, StringConstraints(min_length=8)]
    confirm_password: Annotated[str, StringConstraints(min_length=8)]

    model_config = {
        "json_schema_extra": {
            "example": {
                "password": "Aa@123456789",
                "confirm_password": "Aa@123456789",
            }
        }
    }


class VerifyResetCodeRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {"email": "user@example.com", "code": "123456"}
        }
    }


class AdminUserUpdate(BaseModel):
    """
    Schema for admin to update user information.
    Only allows updating: first_name, last_name, phone, icon, gender, birthday (for both roles), shop (for owner_shop only)
    """

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    icon: Optional[str] = None
    gender: Optional[str] = None
    birthday: Optional[date] = None
    shop: Optional[ShopUpdate] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "first_name": "John",
                "last_name": "Doe",
                "phone": "0123456789",
                "icon": "https://example.com/avatar.jpg",
                "gender": "male",
                "birthday": "2025-09-15",
                "shop": {
                    "name": "New Shop",
                    "phone": "0999999999",
                    "position": "105.8018986,21.0032136",
                    "address": "Đ. Lê Văn Lương, Thanh Xuân, Hà Nội, Vietnam",
                    "logo": "https://example.com/logo.jpg",
                },
            }
        }
    }
