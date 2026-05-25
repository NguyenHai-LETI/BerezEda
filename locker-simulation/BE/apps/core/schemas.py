from typing import Generic, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    status: int = 200
    message: str = "OK"
    data: Optional[T] = None


class ErrorResponse(BaseModel):
    status: int
    message: str
    data: None = None
