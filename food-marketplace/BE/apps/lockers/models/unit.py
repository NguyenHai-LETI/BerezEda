import uuid
from datetime import datetime, timezone
from typing import ClassVar, List, Optional

from sqlalchemy import event
from sqlmodel import Field, Relationship, SQLModel


class LockerUnit(SQLModel, table=True):
    """
    Represents an individual locker unit within a location
    """

    __tablename__: ClassVar[str] = "locker_units"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True
    )
    location_id: str = Field(foreign_key="lockerlocation.id")
    unit_number: int = Field()
    topic_name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="locker unit data provided by galilei via csv",
    )
    full_unit_number: Optional[str] = Field(default=None, max_length=100)
    temperature: Optional[float] = Field(default=None)
    column_index: Optional[int] = Field(default=None, description="Physical column index of the locker cabinet (1-based)")
    status: str = Field(default="AVAILABLE", max_length=20)
    size: str = Field(default="medium")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    location: "LockerLocation" = Relationship(back_populates="units")  # type: ignore
    reservations: List["LockerReservation"] = Relationship(back_populates="unit")  # type: ignore

    def __str__(self):
        return (
            f"{self.location.name if self.location else 'Unknown'} - {self.unit_number}"
        )


# SQLAlchemy Event Listeners for Firebase Sync
@event.listens_for(LockerUnit, "after_insert")
def sync_location_after_unit_insert(mapper, connection, target):
    """Sync location to Firebase after creating a new locker unit"""
    from apps.lockers.tasks import sync_location_to_firebase_task

    if target.location_id:
        sync_location_to_firebase_task.delay(str(target.location_id))


@event.listens_for(LockerUnit, "after_update")
def sync_location_after_unit_update(mapper, connection, target):
    """Sync location to Firebase after updating a locker unit"""
    from apps.lockers.tasks import sync_location_to_firebase_task

    if target.location_id:
        sync_location_to_firebase_task.delay(str(target.location_id))


@event.listens_for(LockerUnit, "after_delete")
def sync_location_after_unit_delete(mapper, connection, target):
    """Sync location to Firebase after deleting a locker unit"""
    from apps.lockers.tasks import sync_location_to_firebase_task

    if target.location_id:
        sync_location_to_firebase_task.delay(str(target.location_id))
