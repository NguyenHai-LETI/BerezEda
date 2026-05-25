import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import event, func, select
from sqlmodel import Field, Relationship, SQLModel


class Review(SQLModel, table=True):
    __tablename__ = "review"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True
    )
    rating: int = Field(default=0)
    comment: Optional[str] = Field(default=None, max_length=2000)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    customer_id: str = Field(foreign_key="user.id", max_length=36, index=True)
    shop_id: str = Field(foreign_key="shop.id", max_length=36, index=True)
    combo_id: str = Field(foreign_key="combo.id", max_length=36)
    order_id: str = Field(foreign_key="orders.id", max_length=36, unique=True, index=True)
    locker_unit_id: Optional[str] = Field(default=None, foreign_key="locker_units.id")

    # One-directional relationships (no back_populates to avoid mapper errors)
    user: Optional["User"] = Relationship()  # type: ignore
    shop: Optional["Shop"] = Relationship()  # type: ignore
    combo: Optional["Combo"] = Relationship()  # type: ignore
    order: Optional["Order"] = Relationship()  # type: ignore
    locker_unit: Optional["LockerUnit"] = Relationship()  # type: ignore


@event.listens_for(Review, "after_insert")
def update_shop_total_reviews_after_insert(mapper, connection, target: "Review"):
    if not getattr(target, "shop_id", None):
        return

    from sqlalchemy.orm import Session
    from apps.shops.models.shops import Shop

    db = Session(bind=connection)

    count_stmt = (
        select(func.count()).select_from(Review).where(Review.shop_id == target.shop_id)
    )
    total = db.execute(count_stmt).scalar() or 0

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
