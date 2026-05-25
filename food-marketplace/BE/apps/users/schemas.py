from typing import Optional
from datetime import date, datetime
from pydantic import BaseModel, EmailStr


class UserRegister(BaseModel):
    email: str
    password: str
    name: Optional[str] = None
    role: str = "customer"


class UserUpdate(BaseModel):
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    birthday: Optional[date] = None
    gender: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: str
    username: Optional[str] = None
    role: str
    permissions: str
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    birthday: Optional[date] = None
    gender: Optional[str] = None
    icon: Optional[str] = None
    is_verified_email: bool
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
