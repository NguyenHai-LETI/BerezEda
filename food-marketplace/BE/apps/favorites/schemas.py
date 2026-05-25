from datetime import datetime

from pydantic import BaseModel


class FavoriteCreate(BaseModel):
    shop_id: str
    is_like: bool = True

    model_config = {
        "json_schema_extra": {
            "example": {
                "shop_id": "013e242f-eeb1-40ee-829f-34e31a0fc05a",
                "is_like": True,
            }
        }
    }


class FavoriteRead(BaseModel):
    id: str
    user_id: str
    shop_id: str
    favorited_at: datetime

    class Config:
        from_attributes = True
