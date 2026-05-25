import uuid
from datetime import datetime
from typing import ClassVar

from sqlmodel import Field, SQLModel
from apps.core.utils import utcnow


class RevokedToken(SQLModel, table=True):
    __tablename__: ClassVar[str] = "revoked_tokens"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True,
        max_length=36,
    )
    jti: str = Field(index=True, unique=True, max_length=64)
    user_id: str = Field(index=True, max_length=36)
    token_type: str = Field(max_length=16)
    expires_at: datetime = Field(index=True)
    created_at: datetime = Field(default_factory=utcnow)
