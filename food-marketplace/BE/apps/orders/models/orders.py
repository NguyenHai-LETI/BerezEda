"""
Order Models

Handles customer orders for combos
"""

import uuid
from datetime import datetime
from typing import ClassVar, Optional

from sqlalchemy import event
from sqlmodel import Field, Relationship, SQLModel

from apps.core.constants import (
    ORDER_STATUS_PICKED_UP,
    UNIT_STATUS_AVAILABLE,
)
from apps.core.utils import get_current_time


class Order(SQLModel, table=True):
    __tablename__: ClassVar[str] = "orders"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True,
        max_length=36,
    )
    user_id: str = Field(foreign_key="user.id", max_length=36, index=True)
    combo_id: str = Field(foreign_key="combo.id", max_length=36, index=True)
    shop_id: str = Field(foreign_key="shop.id", max_length=36, index=True)
    locker_unit_id: Optional[str] = Field(
        foreign_key="locker_units.id", max_length=36, index=True, default=None
    )

    # Order details
    order_number: str = Field(unique=True, index=True, max_length=50)
    status: str = Field(max_length=50, index=True, default="PENDING")

    # Pricing information (captured at time of order)
    original_price: float = Field(ge=0)
    discount_percentage: float = Field(ge=0, le=100, default=0)
    final_price: float = Field(ge=0)

    # Timestamps
    created_at: datetime = Field(default_factory=get_current_time)
    updated_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)

    # Pickup information
    pickup_code: Optional[str] = Field(default=None, max_length=20)
    pickup_deadline: Optional[datetime] = Field(default=None)
    picked_up_at: Optional[datetime] = Field(default=None)
    qr_code_url: Optional[str] = Field(default=None)

    # Payment information (for future expansion)
    payment_method: Optional[str] = Field(default=None, max_length=50)
    # payment_status: Optional[str] = Field(default=None, max_length=50)
    transaction_id: Optional[str] = Field(default=None, max_length=100)

    # Additional notes
    notes: Optional[str] = Field(default=None)

    combo: Optional["Combo"] = Relationship(back_populates="orders")  # type: ignore
    # One-to-one review relationship via Review.order_id
    review: Optional["Review"] = Relationship(
        back_populates="order", sa_relationship_kwargs={"uselist": False}
    )  # type: ignore

    @property
    def is_review(self) -> bool:
        return getattr(self, "review", None) is not None


def _handle_shop_index_update(order: Order, new_status: str) -> None:
    """Update shop's food loss reduction stats in Firebase when order is picked up."""
    from apps.orders.tasks import shop_index_update_firebase_task

    if new_status == ORDER_STATUS_PICKED_UP:
        # Add countdown to ensure DB transaction is committed before task executes
        shop_index_update_firebase_task.apply_async(
            args=[str(order.shop_id)], countdown=2
        )


def _handle_locker_unit_release(connection, order: Order, new_status: str) -> None:
    """Release locker unit and sync to Firebase when order is picked up or cancelled."""
    if new_status != ORDER_STATUS_PICKED_UP:
        return

    if not order.locker_unit_id:
        return

    from sqlalchemy.orm import Session

    from apps.lockers.models.unit import LockerUnit
    from apps.lockers.tasks import sync_location_to_firebase_task

    session = Session(bind=connection)
    locker_unit = session.get(LockerUnit, order.locker_unit_id)

    if not locker_unit:
        return

    # Update locker unit status to available
    locker_unit.status = UNIT_STATUS_AVAILABLE
    session.add(locker_unit)
    session.flush()

    # Trigger Firebase sync for the locker location
    if locker_unit.location_id:
        sync_location_to_firebase_task.delay(str(locker_unit.location_id))


def _send_order_status_notifications(order: Order, new_status: str) -> None:
    """Send notifications to shop and user based on order status changes."""
    from apps.integrations.celery.shops.tasks import send_user_pickup

    if new_status == ORDER_STATUS_PICKED_UP:
        send_user_pickup.delay(combo_id=str(order.combo_id), shop_id=str(order.shop_id))

        # Schedule product expiry notifications at exact expiry_date times
        from apps.integrations.celery.users.tasks import (
            schedule_product_expiry_notifications,
        )

        schedule_product_expiry_notifications.apply_async(
            args=[str(order.combo_id), str(order.user_id)], countdown=2
        )



@event.listens_for(Order, "after_update")
def handle_order_status_change(mapper, connection, target):
    """
    Handle order status changes by triggering appropriate side effects.

    Responsibilities:
    - Update shop revenue in Firebase
    - Update shop food loss reduction stats in Firebase
    - Release locker units and sync to Firebase
    - Send notifications to shop owners and users
    """
    from sqlalchemy.orm import attributes

    status_history = attributes.get_history(target, "status")

    if not status_history.has_changes():
        return

    new_status = target.status

    # Handle all side effects
    _handle_shop_index_update(target, new_status)
    _handle_locker_unit_release(connection, target, new_status)
    _send_order_status_notifications(target, new_status)
