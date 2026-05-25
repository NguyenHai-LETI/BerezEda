import uuid
from datetime import datetime, timezone
from typing import ClassVar, Optional

from sqlalchemy import event, text
from sqlmodel import Field, Relationship, SQLModel

from apps.core.constants import RESERVATION_STATUS_COMPLETED, UNIT_STATUS_AVAILABLE
from apps.core.logging import logger


class LockerReservation(SQLModel, table=True):
    __tablename__: ClassVar[str] = "locker_reservations"

    """
    Represents a reservation or usage of a locker unit
    """

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True
    )
    locker_unit_id: str = Field(foreign_key="locker_units.id")
    user_id: Optional[str] = Field(foreign_key="user.id", default=None)
    shop_id: str = Field(foreign_key="shop.id")
    combo_id: Optional[str] = Field(foreign_key="combo.id", default=None)
    status: str = Field(default="PENDING", max_length=20)
    access_code: Optional[str] = Field(default=None, max_length=50)
    item_deposited_at: Optional[datetime] = Field(default=None)
    item_collected_at: Optional[datetime] = Field(default=None)

    # Timing fields for combo placement and sale
    preparation_deadline: Optional[datetime] = Field(
        default=None
    )  # 20min after reservation
    sale_end_time: Optional[datetime] = Field(default=None)
    price_reduction_time: Optional[datetime] = Field(
        default=None
    )  # When to reduce price

    notes: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # QR code URL stored after first generation (cached in DB)
    qr_code_url: Optional[str] = Field(default=None)

    # Relationships
    unit: "LockerUnit" = Relationship(back_populates="reservations")  # type: ignore
    user: Optional["User"] = Relationship()  # type: ignore
    shop: Optional["Shop"] = Relationship()  # type: ignore
    combo: Optional["Combo"] = Relationship()  # type: ignore

    def __str__(self):
        return f"{self.locker_unit_id} - {self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else 'No timestamp'}"


# SQLAlchemy Event Listeners for Firebase Sync and Unit Status Updates
@event.listens_for(LockerReservation, "after_update")
def sync_location_after_reservation_status_change(mapper, connection, target):
    """Sync location to Firebase and update unit status when reservation status changes"""

    from apps.lockers.tasks import sync_location_to_firebase_task

    # Simple approach - check current status and update unit accordingly
    # This will update the unit status every time, which ensures consistency
    # if target.status == RESERVATION_STATUS_ACTIVE:
    #     # Update LockerUnit status to occupied
    #     if target.locker_unit_id:
    #         connection.execute(
    #             text(
    #                 "UPDATE locker_units SET status = :status, updated_at = :updated_at WHERE id = :unit_id"
    #             ),
    #             {
    #                 "status": UNIT_STATUS_OCCUPIED,
    #                 "updated_at": datetime.now(timezone.utc),
    #                 "unit_id": target.locker_unit_id,
    #             },
    #         )
    #         sync_location_to_firebase_task.delay(target.locker_unit_id, is_unit_id=True)
    # Check if status is completed - update unit to cleaning
    if target.status == RESERVATION_STATUS_COMPLETED:
        if target.locker_unit_id:
            connection.execute(
                text(
                    "UPDATE locker_units SET status = :status, updated_at = :updated_at WHERE id = :unit_id"
                ),
                {
                    "status": UNIT_STATUS_AVAILABLE,  # Per spec: locker unit becomes available after pickup
                    "updated_at": datetime.now(timezone.utc),
                    "unit_id": target.locker_unit_id,
                },
            )

            sync_location_to_firebase_task.delay(target.locker_unit_id, is_unit_id=True)

    # Check if status is cancelled - update unit to available (if was reserved)
    # elif target.status == RESERVATION_STATUS_CANCELLED:
    #     if target.locker_unit_id:
    #         # Only set to available if unit is currently reserved or occupied
    #         connection.execute(
    #             text(
    #                 """
    #                 UPDATE locker_units
    #                 SET status = :status, updated_at = :updated_at
    #                 WHERE id = :unit_id
    #                 AND status IN ('reserved', 'occupied')
    #             """
    #             ),
    #             {
    #                 "status": UNIT_STATUS_AVAILABLE,
    #                 "updated_at": datetime.now(timezone.utc),
    #                 "unit_id": target.locker_unit_id,
    #             },
    #         )
    #         sync_location_to_firebase_task.delay(target.locker_unit_id, is_unit_id=True)


# @event.listens_for(LockerReservation, "after_insert")
# def sync_location_after_reservation_insert(mapper, connection, target):
#     """Sync location to Firebase and update unit status when new reservation is created"""

#     from apps.lockers.tasks import sync_location_to_firebase_task

#     # If created as pending, set unit to reserved
#     if target.status == RESERVATION_STATUS_PENDING and target.locker_unit_id:
#         connection.execute(
#             text(
#                 "UPDATE locker_units SET status = :status, updated_at = :updated_at WHERE id = :unit_id"
#             ),
#             {
#                 "status": UNIT_STATUS_RESERVED,
#                 "updated_at": datetime.now(timezone.utc),
#                 "unit_id": target.locker_unit_id,
#             },
#         )
#         sync_location_to_firebase_task.delay(target.locker_unit_id, is_unit_id=True)

#     # If created as active, set unit to occupied and sync immediately
#     elif target.status == RESERVATION_STATUS_ACTIVE and target.locker_unit_id:
#         connection.execute(
#             text(
#                 "UPDATE locker_units SET status = :status, updated_at = :updated_at WHERE id = :unit_id"
#             ),
#             {
#                 "status": UNIT_STATUS_OCCUPIED,
#                 "updated_at": datetime.now(timezone.utc),
#                 "unit_id": target.locker_unit_id,
#             },
#         )
#         sync_location_to_firebase_task.delay(target.locker_unit_id, is_unit_id=True)
