import uuid
from datetime import datetime
from typing import ClassVar, List, Optional

from sqlalchemy import JSON, Column, event
from sqlmodel import Field, Relationship, Session, SQLModel, select

from apps.core.constants import COMBO_STATUS_SELLING, ORDER_STATUS_PICKED_UP
from apps.core.database import engine


class Combo(SQLModel, table=True):
    TEMPERATURE_CHOICES: ClassVar[list[str]] = ["", "常温", "冷蔵"]
    SALES_DURATION_CHOICES: ClassVar[list[str]] = [
        "30分",
        "1時間",
        "1時間30分",
        "2時間",
        "2時間30分",
        "3時間",
        "6時間",
        "12時間",
        "18時間",
        "24時間",
    ]
    STATUS_PRODUCT: ClassVar[list[str]] = [
        "DRAFT",  # Combo created but not assigned to locker yet
        "PREPARATION_TO_LOCKER",  # Preparation period for placing combo in locker
        "EXPIRED_PUT_IN_LOCKER",  # Expired put in locker
        "SELLING",  # Published and available for purchase
        "SOLD",  # Customer purchased the combo
        "EXPIRED",  # Sales period ended without purchase (terminal)
        "DELETED",  # DELETED by shop/system (terminal)
    ]

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True,
        max_length=36,
    )
    name: str = Field(max_length=1000)
    description: Optional[str] = Field(default=None)
    images: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    is_available: bool = Field(default=True)
    original_price: Optional[float] = Field(default=None)
    discount_percentage: float = Field(default=0)
    product_number: Optional[str] = Field(default=None, max_length=100)
    category: Optional[str] = Field(default="", max_length=100)
    listing_end_date: Optional[datetime] = Field(default=None)
    pickup_deadline: Optional[datetime] = Field(default=None)
    sales_duration: Optional[str] = Field(default=None, max_length=20)
    is_free: bool = Field(default=False)
    is_draft: bool = Field(default=False)
    is_checked: bool = Field(default=False)
    status: str = Field(default="draft", max_length=50)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    edited_at: datetime = Field(default_factory=datetime.utcnow)
    shop_id: str = Field(foreign_key="shop.id", max_length=36, index=True)

    combo_products: List["ComboProduct"] = Relationship(back_populates="combo")  # type: ignore
    shop: Optional["Shop"] = Relationship(back_populates="combos")  # type: ignore
    reviews: List["Review"] = Relationship(back_populates="combo")  # type: ignore
    orders: List["Order"] = Relationship(back_populates="combo")  # type: ignore

    def __str__(self):
        return self.name if self.name else f"Combo {self.id}"

    @property
    def discount_price(self) -> Optional[int]:
        """Calculate the discounted price based on original price and discount percentage."""
        from decimal import ROUND_HALF_UP, Decimal

        if self.original_price is not None:
            discount_amount = (self.discount_percentage / 100) * self.original_price
            return int(
                Decimal(self.original_price - discount_amount).to_integral_value(
                    ROUND_HALF_UP
                )
            )
        return None

    def bought_by(self) -> Optional["User"]:  # type: ignore
        """
        Return the user who bought this combo.

        Finds the user who placed an order for this combo.
        Typically there should only be one order per combo.

        Returns:
            Optional[User]: The user who purchased this combo, or None if no orders exist
        """
        if not self.orders or len(self.orders) == 0:
            return None

        # Get the first order (should typically be only one order per combo)
        order = self.orders[0]

        # The Order model has user_id but may not have loaded user relationship
        # We need to fetch it from the database if not already loaded
        if hasattr(order, "user") and order.user:
            return order.user

        # If user is not loaded, fetch it using user_id
        if order.user_id:
            from apps.users.models import User

            with Session(engine) as session:
                user = session.exec(
                    select(User).where(User.id == order.user_id)
                ).first()
                return user

        return None


@event.listens_for(Combo, "after_update")
def sync_combo_after_update(mapper, connection, target):
    """Sync to Firebase after updating a combo - when status changes to selling OR when draft becomes false"""
    from sqlalchemy.orm import attributes

    from apps.products.tasks import sync_combo_to_firebase_task

    # Get the instance state to check for changes
    attributes.instance_state(target)

    # Check if status attribute was modified
    status_history = attributes.get_history(target, "status")
    is_draft_history = attributes.get_history(target, "is_draft")

    should_sync = False
    should_sync_shop_analytics = False

    # Case 1: Status changes to 'selling'
    if status_history.has_changes():
        old_status = status_history.deleted[0] if status_history.deleted else None
        new_status = target.status

        if old_status != COMBO_STATUS_SELLING and new_status == COMBO_STATUS_SELLING:
            should_sync = True

            # Send notification to users who favorited this store
            from apps.integrations.celery.users.tasks import (
                send_favorite_shop_add_new_combo,
            )

            send_favorite_shop_add_new_combo.delay(
                combo_id=str(target.id), shop_id=str(target.shop_id)
            )

        # Sync shop analytics when status changes to picked_up (affects metrics)
        if new_status == ORDER_STATUS_PICKED_UP:
            should_sync_shop_analytics = True

    # Case 2: is_draft changes from True to False
    if is_draft_history.has_changes():
        old_is_draft = is_draft_history.deleted[0] if is_draft_history.deleted else None
        new_is_draft = target.is_draft

        if old_is_draft == True and new_is_draft == False:
            should_sync = True

    # Sync to Firebase if any condition is met
    # countdown=2 ensures the task runs after the DB transaction is committed,
    # preventing a race condition where the task reads stale data (sale_end_time=null)
    # before the transaction completes.
    if should_sync:
        sync_combo_to_firebase_task.apply_async(args=[str(target.id)], countdown=2)

    # Sync shop analytics to Firebase if needed
    if should_sync_shop_analytics:
        from apps.shops.tasks import sync_shop_analytics_to_firebase_task

        sync_shop_analytics_to_firebase_task.delay(str(target.shop_id))


@event.listens_for(Combo, "after_delete")
def sync_combo_after_delete(mapper, connection, target):
    """Remove from Firebase after deleting a combo"""
    from apps.products.tasks import delete_shop_combo_from_firebase_task

    # When a combo is deleted, remove the shop's record from Firebase
    # and sync the next newest combo for that shop (if any)
    delete_shop_combo_from_firebase_task.delay(str(target.shop_id))
