from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, field_validator


class QrcodeRead(BaseModel):
    id: str
    qr_data: str
    is_used: bool = False
    created_at: datetime
    user_id: Optional[str] = None
    is_active: bool = True
    image_url: Optional[str] = None

    model_config = {"from_attributes": True}


class QrcodeGenerateRequest(BaseModel):
    count: int = 1

    @field_validator("count")
    @classmethod
    def validate_count(cls, v):
        if v < 1 or v > 100:
            raise ValueError("Count must be at least 1 and no more than 100")
        return v

    model_config = {"json_schema_extra": {"example": {"count": 2}}}


class QrcodeGenerateResponse(BaseModel):
    total_generated: int
    qrcodes: List[QrcodeRead]

    model_config = {"from_attributes": True}


class QrcodeVerifyRequest(BaseModel):
    qr_data: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "qr_data": "QR_1759754589_GkzdC4Vw",
            }
        }
    }


class QrcodeListResponse(BaseModel):
    qrcodes: List[QrcodeRead]
    total: int
    limit: int
    offset: int
