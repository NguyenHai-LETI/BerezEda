import uuid
from datetime import datetime, timezone
from typing import ClassVar, Optional

from sqlmodel import Field, Relationship, SQLModel


class NotificationUser(SQLModel, table=True):
    # Status constants
    PENDING: ClassVar[str] = "pending"
    SENT: ClassVar[str] = "sent"
    FAILED: ClassVar[str] = "failed"
    STATUS_CHOICES: ClassVar[list[str]] = ["pending", "sent", "failed"]

    # Channel constants
    IN_APP: ClassVar[str] = "in-app"
    EMAIL: ClassVar[str] = "email"
    PUSH: ClassVar[str] = "push"
    SMS: ClassVar[str] = "sms"
    CHANNEL_CHOICES: ClassVar[list[str]] = ["in-app", "email", "push", "sms"]

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True
    )
    notification_id: str = Field(foreign_key="notification.id")
    user_id: str = Field(foreign_key="user.id")
    is_read: bool = Field(default=False)
    is_confirmed: bool = Field(default=False)
    confirm_content: Optional[str] = Field(default=None, max_length=255)
    read_at: Optional[datetime] = Field(default=None)
    confirmed_at: Optional[datetime] = Field(default=None)
    sent_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = Field(default="pending", max_length=20)
    channel: Optional[str] = Field(default=None, max_length=20)
    skipped_by_user_settings: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notification: Optional["Notification"] = Relationship(
        back_populates="notification_user"
    )

    # Relationships (optional, if you want to use SQLModel's Relationship)
    # notification: Optional["Notification"] = Relationship(back_populates="user_notifications")
    # user: Optional["User"] = Relationship(back_populates="notifications")

    # def __str__(self):
    #     return f"{self.user_id} - {self.notification_id}"
