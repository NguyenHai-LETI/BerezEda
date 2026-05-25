from datetime import datetime, timezone
from typing import ClassVar, List, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel


class Device(SQLModel, table=True):
    PLATFORM_IOS: ClassVar[str] = "ios"
    PLATFORM_ANDROID: ClassVar[str] = "android"
    PLATFORM_WEB: ClassVar[str] = "web"
    PLATFORM_OTHER: ClassVar[str] = "other"
    PLATFORM_CHOICES: ClassVar[List[str]] = [
        PLATFORM_IOS,
        PLATFORM_ANDROID,
        PLATFORM_WEB,
        PLATFORM_OTHER,
    ]

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    user_id: Optional[str] = Field(
        default=None, foreign_key="user.id", max_length=36, nullable=True
    )
    device_token: str = Field()
    platform: str = Field(max_length=10)
    position: Optional[str] = Field(
        default=None, description="GeoJSON Point as string (longitude, latitude)"
    )
    last_active: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    user: Optional["User"] = Relationship(back_populates="devices")  # type: ignore

    def __str__(self):
        return f"{self.user_id} - {self.platform} - {self.device_token}"
