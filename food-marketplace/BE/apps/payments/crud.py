from typing import Optional, List
from sqlmodel import Session, select

from apps.core.utils import utcnow

from apps.payments.models import Card, FincodeUser, Payment


# ── FincodeUser ──────────────────────────────────────────────────────────────

def get_fincode_user(db: Session, user_id: str) -> Optional[FincodeUser]:
    return db.exec(select(FincodeUser).where(FincodeUser.user_id == user_id)).first()


def create_fincode_user(db: Session, user_id: str, fincode_customer_id: str) -> FincodeUser:
    fu = FincodeUser(user_id=user_id, fincode_customer_id=fincode_customer_id)
    db.add(fu)
    db.commit()
    db.refresh(fu)
    return fu


# ── Card ─────────────────────────────────────────────────────────────────────

def get_cards_by_customer(db: Session, customer_id: str) -> List[Card]:
    return db.exec(select(Card).where(Card.customer_id == customer_id)).all()


def count_cards_by_customer(db: Session, customer_id: str) -> int:
    return len(db.exec(select(Card).where(Card.customer_id == customer_id)).all())


def get_card_by_id(db: Session, card_id: str) -> Optional[Card]:
    return db.get(Card, card_id)


def get_card_by_fincode_id(db: Session, customer_id: str, fincode_card_id: str) -> Optional[Card]:
    return db.exec(
        select(Card).where(Card.customer_id == customer_id, Card.fincode_card_id == fincode_card_id)
    ).first()


def create_card(db: Session, data: dict) -> Card:
    card = Card(**data)
    db.add(card)
    db.commit()
    db.refresh(card)
    return card


def set_card_default(db: Session, customer_id: str, card_id: str) -> None:
    """Mark one card as default, clear default from others."""
    cards = db.exec(select(Card).where(Card.customer_id == customer_id)).all()
    for c in cards:
        c.is_default = (c.id == card_id)
        db.add(c)
    db.commit()


def delete_card(db: Session, card: Card) -> None:
    db.delete(card)
    db.commit()


# ── Payment ──────────────────────────────────────────────────────────────────

def create_payment(db: Session, data: dict) -> Payment:
    payment = Payment(**data)
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def update_payment(db: Session, payment: Payment, data: dict) -> Payment:
    for k, v in data.items():
        setattr(payment, k, v)
    payment.updated_at = utcnow()
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def get_payment_by_fincode_id(db: Session, fincode_payment_id: str) -> Optional[Payment]:
    return db.exec(select(Payment).where(Payment.fincode_payment_id == fincode_payment_id)).first()
