from typing import Optional, List
from sqlmodel import Session, select

from apps.core.utils import utcnow

from apps.orders.models import Order


def get_order_by_id(db: Session, order_id: str) -> Optional[Order]:
    return db.get(Order, order_id)


def get_orders_by_customer(
    db: Session, customer_id: str,
    year: Optional[int] = None,
    month: Optional[int] = None,
) -> List[Order]:
    q = select(Order).where(Order.customer_id == customer_id)
    if year and month:
        from sqlalchemy import extract
        q = q.where(
            extract("year", Order.created_at) == year,
            extract("month", Order.created_at) == month,
        )
    return db.exec(q.order_by(Order.created_at.desc())).all()


def get_orders_by_shop(db: Session, shop_id: str) -> List[Order]:
    return db.exec(select(Order).where(Order.shop_id == shop_id).order_by(Order.created_at.desc())).all()


def create_order(db: Session, data: dict) -> Order:
    order = Order(**data)
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def update_order(db: Session, order: Order, data: dict) -> Order:
    for k, v in data.items():
        setattr(order, k, v)
    order.updated_at = utcnow()
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def get_order_by_fincode_payment_id(db: Session, payment_id: str) -> Optional[Order]:
    return db.exec(select(Order).where(Order.fincode_payment_id == payment_id)).first()


def find_order_by_access_code(db: Session, access_code: str, customer_id: str) -> Optional[Order]:
    from sqlmodel import select
    return db.exec(
        select(Order).where(
            Order.access_code == access_code,
            Order.customer_id == customer_id,
            Order.status == "paid",
        )
    ).first()
