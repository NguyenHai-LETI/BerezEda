import uuid
from datetime import datetime
from typing import ClassVar, List, Optional, Union

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship, SQLModel


class ComboProduct(SQLModel, table=True):
    """Junction table for many-to-many relationship between Combo and ProductMaster"""

    __tablename__: ClassVar[str] = "combo_products"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True,
        max_length=36,
    )
    combo_id: str = Field(foreign_key="combo.id", max_length=36, index=True)
    product_master_id: str = Field(
        foreign_key="product_masters.id", max_length=36, index=True
    )
    quantity: int = Field(default=1, ge=1)  # quantity must be at least 1
    expiry_dates: Optional[List[Union[datetime, str]]] = Field(
        default=None, sa_column=Column(JSON)
    )  # list of expiry dates based on quantity
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    combo: Optional["Combo"] = Relationship(back_populates="combo_products")  # type: ignore
    product_master: Optional["ProductMaster"] = Relationship(back_populates="combo_products")  # type: ignore

    def __setattr__(self, name: str, value) -> None:
        """Override setattr to convert datetime objects to ISO strings for JSON storage"""
        if name == "expiry_dates" and value is not None:
            # Convert datetime objects to ISO format strings for JSON storage
            if isinstance(value, list):
                converted_dates = []
                for date in value:
                    if isinstance(date, datetime):
                        converted_dates.append(date.isoformat())
                    else:
                        converted_dates.append(date)
                value = converted_dates
        super().__setattr__(name, value)
