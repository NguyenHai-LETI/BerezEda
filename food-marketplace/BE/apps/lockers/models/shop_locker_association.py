import uuid
from datetime import datetime, timezone
from typing import ClassVar, Optional

from sqlalchemy import event
from sqlmodel import Field, SQLModel


class ShopLockerAssociation(SQLModel, table=True):
    """
    Association table for many-to-many relationship between shops and locker locations
    """

    __tablename__: ClassVar[str] = "shop_locker_associations"

    shop_id: str = Field(foreign_key="shop.id", primary_key=True)
    locker_location_id: str = Field(foreign_key="lockerlocation.id", primary_key=True)
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), index=True)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# SQLAlchemy Event Listeners for Firebase Sync
@event.listens_for(ShopLockerAssociation, "after_insert")
def sync_location_after_association_insert(mapper, connection, target):
    """Sync location to Firebase after adding a shop association"""
    from apps.lockers.tasks import sync_location_to_firebase_task

    sync_location_to_firebase_task.delay(str(target.locker_location_id))


@event.listens_for(ShopLockerAssociation, "after_delete")
def sync_location_after_association_delete(mapper, connection, target):
    """Sync location to Firebase after removing a shop association"""
    from apps.lockers.tasks import sync_location_to_firebase_task

    sync_location_to_firebase_task.delay(str(target.locker_location_id))
