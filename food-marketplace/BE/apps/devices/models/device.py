import uuid
from datetime import datetime
from sqlmodel import Field, SQLModel
from apps.core.utils import utcnow


class Device(SQLModel, table=True):
    __tablename__ = "device"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, max_length=36)
    user_id: str = Field(max_length=36, index=True)
    fcm_token: str = Field(max_length=500, index=True)
    platform: str = Field(default="web", max_length=20)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
