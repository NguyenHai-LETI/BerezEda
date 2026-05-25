import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel
from apps.core.utils import utcnow


class Notification(SQLModel, table=True):
    __tablename__ = "notification"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, max_length=36)
    user_id: str = Field(max_length=36, index=True)
    title: str = Field(max_length=200)
    body: str = Field(max_length=1000)
    notification_type: str = Field(max_length=50)
    reference_id: Optional[str] = Field(default=None, max_length=36)
    is_read: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utcnow)
