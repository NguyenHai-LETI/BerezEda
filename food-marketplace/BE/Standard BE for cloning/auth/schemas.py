from typing import Optional

from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            }
        }
    }


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
                "password": "Aa@12345678",
                "shop_code": "SHOP001",
            }
        }
    }


class UserAuth(BaseModel):
    username: str
    email: Optional[EmailStr] = None


class LogoutRequest(BaseModel):
    device_token: Optional[str] = None
    refresh_token: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "device_token": "cIm7ce_yv0gClr0oEBHccZ:APA91bGR8iTxxTCrYAedkDETWuEu0oRbZF0nAfdF3jpOkIftfLAd1so5xoXD4mQ1Rd0epjRLp-3VH9z_P2HU2cl7ncQQLxCe-kfxwmGKkveiSo3S7-ixAMw"
            }
        }
    }
    full_name: Optional[str] = None
    disabled: Optional[bool] = None


class UserInDB(UserAuth):
    hashed_password: str
