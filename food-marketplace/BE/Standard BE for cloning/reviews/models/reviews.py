import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import event, func, select
from sqlmodel import Field, Relationship, SQLModel


class Review(SQLModel, table=True):
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True
    )
    rating: int = Field(default=0)
    comment: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: str = Field(foreign_key="user.id")
    shop_id: Optional[str] = Field(default=None, foreign_key="shop.id")
    combo_id: Optional[str] = Field(default=None, foreign_key="combo.id")
    order_id: Optional[str] = Field(default=None, foreign_key="orders.id")
    locker_unit_id: Optional[str] = Field(default=None, foreign_key="locker_units.id")

    # Relationships
    user: Optional["User"] = Relationship(back_populates="reviews")  # type: ignore
    shop: Optional["Shop"] = Relationship(back_populates="reviews")  # type: ignore
    combo: Optional["Combo"] = Relationship(back_populates="reviews")  # type: ignore
    order: Optional["Order"] = Relationship(back_populates="review")  # type: ignore
    locker_unit: Optional["LockerUnit"] = Relationship()  # type: ignore


@event.listens_for(Review, "after_insert")
def update_shop_total_reviews_after_insert(mapper, connection, target: "Review"):
    """Update Shop.total_reviews after a new review is inserted.

    Counts all reviews for the associated shop_id and writes the value to the
    corresponding Shop.total_reviews field. Uses the same transaction via the
    provided connection.
    """
    if not getattr(target, "shop_id", None):
        return

    from sqlalchemy.orm import Session

    from apps.shops.models.shops import Shop

    db = Session(bind=connection)

    count_stmt = (
        select(func.count()).select_from(Review).where(Review.shop_id == target.shop_id)
    )
    # Use SQLAlchemy execution API (staging uses plain Session without SQLModel.exec)
    total = db.execute(count_stmt).scalar() or 0

    # Calculate average rating rounded to 2 decimals
    sum_stmt = select(func.coalesce(func.sum(Review.rating), 0)).where(
        Review.shop_id == target.shop_id
    )
    total_rating = db.execute(sum_stmt).scalar() or 0
    avg_rating = round((total_rating / total), 2) if total else 0.0

    shop = db.get(Shop, target.shop_id)
    if shop:
        shop.total_reviews = int(total)
        shop.avg_rating = float(avg_rating)
        db.add(shop)
        db.flush()
