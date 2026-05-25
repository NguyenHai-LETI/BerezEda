import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class Favorite(SQLModel, table=True):
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True,
        max_length=36,
    )
    user_id: str = Field(foreign_key="user.id", index=True, max_length=36)
    shop_id: str = Field(foreign_key="shop.id", index=True, max_length=36)
    favorited_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    shop: Optional["Shop"] = Relationship(back_populates="favorite")  # type: ignore
    user: Optional["User"] = Relationship(back_populates="favorites")  # type: ignore
