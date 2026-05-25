import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel
from apps.core.utils import utcnow


class Favorite(SQLModel, table=True):
    __tablename__ = "favorite"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, max_length=36)
    user_id: str = Field(foreign_key="user.id", max_length=36, index=True)
    shop_id: str = Field(foreign_key="shop.id", max_length=36, index=True)
    favorited_at: datetime = Field(default_factory=utcnow, index=True)
    created_at: datetime = Field(default_factory=utcnow)

    shop: Optional["Shop"] = Relationship()  # type: ignore
    user: Optional["User"] = Relationship(back_populates="favorites")  # type: ignore
