import uuid
from datetime import datetime
from typing import ClassVar

from pydantic import validator
from sqlmodel import Field, SQLModel

PAY_TYPE = ["Card", "Paypay", "Applepay"]

PAYMENT_STATUS = [
    "UNPROCESSED",
    "AUTHENTICATED",
    "PROCESSED",
    "FAILED",
]
JOB_CODE = ["AUTH", "CAPTURE", "CHECK"]


class UserFincode(SQLModel, table=True):
    __tablename__: ClassVar[str] = "fincode_user"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True,
        max_length=36,
    )
    user_id: str = Field(foreign_key="user.id", index=True, max_length=36)
    card_registration: str = Field(default="0", max_length=1)
    directdebit_registration: str = Field(default="0", max_length=1)
    created: datetime = Field(default_factory=datetime.utcnow)
    updated: datetime = Field(default_factory=datetime.utcnow)


class Card(SQLModel, table=True):
    __tablename__: ClassVar[str] = "card"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True,
        max_length=36,
    )
    user_id: str = Field(foreign_key="user.id", index=True, max_length=36)
    card_id: str = Field(index=True, nullable=False, max_length=36)
    created: datetime = Field(default_factory=datetime.utcnow)
    updated: datetime = Field(default_factory=datetime.utcnow)

    @validator("created", "updated", pre=True)
    def parse_datetime(cls, value):
        if isinstance(value, str):
            return (datetime.strptime(value, "%Y/%m/%d %H:%M:%S.%f"),)
        return value
