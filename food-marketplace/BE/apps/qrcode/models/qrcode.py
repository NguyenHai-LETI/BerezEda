import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Qrcode(SQLModel, table=True):

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True
    )
    user_id: Optional[str] = Field(
        default=None,
        foreign_key="user.id",
        description="ID of the poor person assigned this QR code",
    )
    qr_data: str = Field(max_length=1000, description="Data encoded in the QR code")
    is_used: bool = Field(
        default=False, description="Whether the QR code has been used"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True, description="Whether the QR code is active")
    image_url: Optional[str] = Field(
        default=None, description="URL of the QR code image"
    )
