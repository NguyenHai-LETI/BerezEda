from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DeviceCreate(BaseModel):
    device_token: str = Field(
        ..., description="Unique device token for push notifications"
    )
    platform: str = Field(..., description="Device platform (ios, android, web)")
    position: Optional[str] = Field(
        default=None, description="GeoJSON Point as string (longitude, latitude)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "device_token": "APNs-token-or-FCM-token-here",
                "platform": "ios",
                "position": "139.6917, 35.6895",
            }
        }
    }


class DeviceUpdate(BaseModel):
    device_token: str = Field(..., description="Device token to update user_id for")

    model_config = {
        "json_schema_extra": {
            "example": {
                "device_token": "APNs-token-or-FCM-token-here",
            }
        }
    }


class DeviceRead(BaseModel):
    id: UUID
    user_id: Optional[str] = None
    device_token: str
    platform: str
    position: Optional[str] = None
    last_active: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
