import uuid
from datetime import datetime, timezone
from typing import ClassVar, Optional

from sqlmodel import Field, Relationship, SQLModel


class Notification(SQLModel, table=True):
    # Class constants for message types
    INFO: ClassVar[str] = "info"
    WARNING: ClassVar[str] = "warning"
    SYSTEM: ClassVar[str] = "system"
    MESSAGE_TYPE_CHOICES: ClassVar[list[str]] = ["info", "warning", "system"]

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True
    )
    title: str = Field(max_length=255)
    body: str = Field(default="")
    type: str = Field(default="info", max_length=20)
    notification_type: Optional[str] = Field(default=None, max_length=50)
    target_type: Optional[str] = Field(default=None, max_length=50)
    target_id: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by_id: Optional[str] = Field(default=None, foreign_key="user.id")
    notification_user: Optional["NotificationUser"] = Relationship(
        back_populates="notification"
    )
    # created_by: Optional["User"] = Relationship(back_populates="created_notifications")
