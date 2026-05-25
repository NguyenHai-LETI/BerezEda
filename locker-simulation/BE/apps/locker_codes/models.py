import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LockerCode(SQLModel, table=True):
    __tablename__ = "locker_codes"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    code: str = Field(max_length=10, index=True)
    code_type: str = Field(max_length=2)
    numeric_part: str = Field(max_length=6)
    locker_unit_id: str = Field(max_length=36, index=True)
    location_id: str = Field(max_length=36)
    combo_id: Optional[str] = Field(default=None, max_length=36)
    order_id: Optional[str] = Field(default=None, max_length=36)
    is_active: bool = Field(default=True, index=True)
    expires_at: Optional[datetime] = Field(default=None)
    used_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=utcnow)
