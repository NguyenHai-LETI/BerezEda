from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


class LockerUnitResponse(BaseModel):
    id: str
    unit_number: int
    status: str
    temperature: Optional[float] = None
    size: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class LockerLocationResponse(BaseModel):
    id: str
    owner_id: str
    name: str
    description: Optional[str] = None
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    image: Optional[str] = None
    is_active: bool
    units: List[LockerUnitResponse] = []
    distance_km: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LockerLocationCreate(BaseModel):
    name: str
    description: Optional[str] = None
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    unit_count: Optional[int] = 0  # auto-create N units on creation


class LockerLocationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_active: Optional[bool] = None


class LockerUnitCreate(BaseModel):
    unit_number: Optional[int] = None  # auto-assigned if None
    temperature: Optional[float] = None
    size: Optional[str] = None


class LockerUnitUpdate(BaseModel):
    status: Optional[str] = None
    temperature: Optional[float] = None
    size: Optional[str] = None
    is_active: Optional[bool] = None


class FavoriteLockerResponse(BaseModel):
    id: str
    user_id: str
    locker_location_id: str
    locker: Optional[LockerLocationResponse] = None
    created_at: datetime

    class Config:
        from_attributes = True
