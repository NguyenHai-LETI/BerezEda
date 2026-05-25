import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class FavoriteLocker(SQLModel, table=True):
    """User's favorite locker locations (max 3 per user)."""

    __tablename__ = "favorite_locker"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True,
        max_length=36,
    )
    user_id: str = Field(foreign_key="user.id", index=True, max_length=36)
    locker_location_id: str = Field(
        foreign_key="lockerlocation.id", index=True, max_length=36
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user: Optional["User"] = Relationship(back_populates="favorite_lockers")  # type: ignore
    locker_location: Optional["LockerLocation"] = Relationship(  # type: ignore
        back_populates="favorite_lockers"
    )
