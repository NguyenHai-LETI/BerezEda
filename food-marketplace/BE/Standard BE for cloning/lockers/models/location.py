import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import event
from sqlmodel import Field, Relationship, SQLModel

# Import the association model
from apps.lockers.models.shop_locker_association import ShopLockerAssociation


class LockerLocation(SQLModel, table=True):
    """
    Represents a physical location where lockers are installed (e.g., a train station)
    """

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True
    )
    name: str = Field(max_length=255)
    code: str = Field(max_length=50, unique=True)
    address: Optional[str] = Field(default=None, max_length=500)
    description: Optional[str] = Field(default=None)
    phone: Optional[str] = Field(default=None, max_length=20)
    image: Optional[str] = Field(default=None)
    # Store position as a string (GeoJSON or "lat,lng")
    position: Optional[str] = Field(
        default=None, description="Geographic location of the shop"
    )
    owner_id: str = Field(
        foreign_key="user.id",
        max_length=36,
        index=True,
        description="ID of the owner_locker who owns this location",
    )
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    units: List["LockerUnit"] = Relationship(back_populates="location")  # type: ignore
    shops: List["Shop"] = Relationship(  # type: ignore
        back_populates="locker_locations", link_model=ShopLockerAssociation
    )
    owner: Optional["User"] = Relationship(back_populates="owned_locker_locations")  # type: ignore
    favorite_lockers: List["FavoriteLocker"] = Relationship(  # type: ignore
        back_populates="locker_location"
    )

    def __str__(self):
        return self.name


# SQLAlchemy Event Listeners for Firebase Sync
@event.listens_for(LockerLocation, "after_insert")
def sync_location_after_insert(mapper, connection, target):
    """Sync location to Firebase after creating a new locker location"""
    from apps.lockers.tasks import sync_location_to_firebase_task

    sync_location_to_firebase_task.delay(str(target.id))


@event.listens_for(LockerLocation, "after_update")
def sync_location_after_update(mapper, connection, target):
    """Sync location to Firebase after updating a locker location"""
    from apps.lockers.tasks import sync_location_to_firebase_task

    sync_location_to_firebase_task.delay(str(target.id))


@event.listens_for(LockerLocation, "after_delete")
def sync_location_after_delete(mapper, connection, target):
    """Remove location from Firebase after deleting a locker location"""
    from apps.lockers.tasks import delete_location_from_firebase_task

    delete_location_from_firebase_task.delay(str(target.id))
