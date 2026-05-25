from typing import TypeVar, Generic, Optional, List, Any
from pydantic import BaseModel

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    status: int = 200
    message: str = "OK"
    data: Optional[T] = None


class ListResponse(BaseModel, Generic[T]):
    status: int = 200
    message: str = "OK"
    data: List[T] = []
    total: int = 0


class ErrorResponse(BaseModel):
    status: int
    message: str
    error_code: Optional[str] = None
    errors: Optional[Any] = None
