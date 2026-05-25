import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class LockerSearchHistory(SQLModel, table=True):
    """User's locker search history (max 5 unique locations per user)."""

    __tablename__ = "locker_search_history"

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
    searched_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), index=True
    )
