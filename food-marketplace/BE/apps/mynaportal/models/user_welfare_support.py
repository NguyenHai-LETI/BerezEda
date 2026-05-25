import uuid
from datetime import datetime, timezone
from typing import ClassVar, Optional

from sqlmodel import Field, Relationship, SQLModel


class UserWelfareSupport(SQLModel, table=True):
    """Model to store user welfare support information from Mynaportal."""

    __tablename__: ClassVar[str] = "user_welfare_supports"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True,
        max_length=36,
    )
    user_id: str = Field(foreign_key="user.id", index=True)
    welfare_type: str = Field(max_length=100, index=True)
    start_date: str = Field(max_length=20)
    end_date: str = Field(max_length=20)
    myna_authorizer_id: Optional[str] = Field(
        default=None, foreign_key="myna_authorizers.id", index=True
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    user: Optional["User"] = Relationship(back_populates="welfare_supports")  # type: ignore
    myna_authorizer: Optional["MynaAuthorizer"] = Relationship()  # type: ignore

    def __str__(self):
        return f"UserWelfareSupport({self.welfare_type}, {self.start_date}-{self.end_date})"
