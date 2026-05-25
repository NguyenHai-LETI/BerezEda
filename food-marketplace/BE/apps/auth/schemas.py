from typing import Optional

from pydantic import BaseModel, EmailStr


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RefreshToken(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserLogin(BaseModel):
    username: str
    password: str
    shop_code: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "username": "admin@example.com",
                "password": "Admin@123",
                "shop_code": None,
            }
        }
    }


class LogoutRequest(BaseModel):
    device_token: Optional[str] = None
    refresh_token: Optional[str] = None
