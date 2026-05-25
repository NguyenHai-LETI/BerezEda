import uuid
from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, Optional

from sqlalchemy import JSON
from sqlmodel import Column, Field, Relationship, SQLModel


class MynaAuthorizer(SQLModel, table=True):
    __tablename__: ClassVar[str] = "myna_authorizers"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True
    )
    user_id: Optional[str] = Field(default=None, foreign_key="user.id")

    error_description: Optional[str] = Field(default="")
    code: Optional[str] = Field(default="")
    state: Optional[str] = Field(default=None)
    status: str = Field(default="INIT")
    access_token: Optional[str] = Field(default="")
    error_response: Optional[str] = Field(default="")
    oauth_token_response: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSON)
    )
    request_response: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSON)
    )
    telegramId: Optional[str] = Field(default="")
    processId: Optional[str] = Field(default="")
    result_response: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSON)
    )
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    user: Optional["User"] = Relationship(back_populates="myna_authorizers")  # type: ignore

    def __str__(self):
        return f"MynaAuthorizer({self.id})"
