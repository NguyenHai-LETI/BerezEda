from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

from pydantic import BaseModel, field_validator
from pydantic.generics import GenericModel

from .utils import parse_position_string

T = TypeVar("T")

DEFAULT_LIMIT = 21
DEFAULT_OFFSET = 0


class PositionParserMixin(BaseModel):
    """
    Mixin class that provides position parsing functionality.

    This mixin automatically converts position strings to GeoJSON Point format
    in API responses while allowing string input for create/update operations.

    Usage:
        class MyLocationSchema(PositionParserMixin, BaseModel):
            name: str
            # position field is inherited from mixin

    Features:
        - Accepts string input: "35.6812,139.7671"
        - Returns GeoJSON format: {"type": "Point", "coordinates": [35.6812, 139.7671]}
        - Handles already parsed GeoJSON objects
        - Returns None for empty/invalid values
    """

    position: Optional[Union[Dict[str, Union[str, List[float]]], None]] = None

    @field_validator("position", mode="before")
    @classmethod
    def parse_position(cls, v):
        """Convert position string to GeoJSON Point format"""
        # If it's already a dict (GeoJSON), return as is
        if isinstance(v, dict):
            return v

        # If it's a string, parse it
        if isinstance(v, str) and v.strip():
            try:
                return parse_position_string(v)
            except (ValueError, IndexError) as e:
                # Could use logging here instead of print in production
                print(f"Failed to parse position '{v}': {e}")
                return None

        # Return None for empty/null values
        return None


class SuccessResponse(GenericModel, Generic[T]):
    status: int = 200
    message: str = "successful"
    data: Optional[T] = None


class ListResponse(GenericModel, Generic[T]):
    limit: int
    offset: int
    total: int
    status: int = 200
    message: str = "successful"
    data: Optional[list[T]] = None


class ErrorResponse(BaseModel):
    status: int = 400
    message: str
    error_code: Optional[str] = None
    errors: Optional[Any] = None
