import uuid
from datetime import datetime, timezone
from typing import ClassVar

from sqlmodel import Field, SQLModel


class ShopCooldown(SQLModel, table=True):
    """
    Tracks shop cooldown periods after failed locker placements
    """

    __tablename__: ClassVar[str] = "shop_cooldowns"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True
    )
    shop_id: str = Field(foreign_key="shop.id", index=True)
    failed_reservation_id: str = Field(foreign_key="locker_reservations.id")
    cooldown_start: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    cooldown_end: datetime = Field()
    reason: str = Field(default="preparation_timeout", max_length=50)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def __str__(self):
        return f"Shop {self.shop_id} - Cooldown until {self.cooldown_end.strftime('%H:%M:%S')}"
