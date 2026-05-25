from datetime import datetime, timedelta
from typing import Optional

from sqlmodel import Session, select

from apps.core.utils import get_current_time
from apps.purchase.constants import TDS2_TYPE_DEFAULT, TDS_TYPE_DEFAULT
from apps.purchase.models.payments import Payment
from apps.purchase.models.users_fincode import Card, UserFincode


def get_user_fincode(db: Session, user_id: str):
    return db.get(UserFincode, user_id)


def create_user_fincode(db: Session, user: UserFincode) -> UserFincode:
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_card(db: Session, card_record: Card) -> Card:
    db.add(card_record)
    db.commit()
    db.refresh(card_record)
    return card_record


def delete_card(db: Session, user_id: str, card_id: str):
    statement = select(Card).where(Card.user_id == user_id, Card.card_id == card_id)
    card = db.exec(statement).first()
    if card:
        db.delete(card)
        db.commit()


def get_card_by_customer_id(db: Session, customer_id: str) -> Optional[Card]:
    statement = select(Card).where(Card.user_id == customer_id)
    return db.exec(statement).first()


def get_payment_by_order_id(db: Session, order_id: str) -> Optional[Payment]:
    statement = select(Payment).where(Payment.order_id == order_id)
    return db.exec(statement).first()


def update_user_fincode(db: Session, user_id: str) -> Optional[UserFincode]:
    """Update existing UserFincode with fincode_customer_id"""
    user_fincode = get_user_fincode(db, user_id)
    if user_fincode:
        user_fincode.user_id = user_id
        user_fincode.updated = get_current_time()
        db.add(user_fincode)
        db.commit()
        db.refresh(user_fincode)
    return user_fincode


def create_payment(db: Session, payment: Payment):
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def get_payment_by_id(db: Session, payment_id: str) -> Optional[Payment]:
    statement = select(Payment).where(Payment.id == payment_id)
    return db.exec(statement).first()


def update_payment(
    db: Session, payment_id: str, fincode_response: dict
) -> Optional[Payment]:

    payment = get_payment_by_id(db, payment_id)
    if not payment:
        return None

    payment.pay_type = fincode_response.get("pay_type", payment.pay_type)
    payment.job_code = fincode_response.get("job_code", payment.job_code)
    payment.amount = (
        int(fincode_response.get("amount", payment.amount))
        if fincode_response.get("amount") is not None
        else payment.amount
    )
    payment.tds_type = fincode_response.get("tds_type") or TDS_TYPE_DEFAULT
    payment.tds2_type = fincode_response.get("tds2_type") or TDS2_TYPE_DEFAULT
    payment.client_field_1 = fincode_response.get(
        "client_field_1", payment.client_field_1
    )

    payment.card_id = fincode_response.get("card_id", payment.card_id)
    payment.customer_id = fincode_response.get("customer_id", payment.customer_id)
    payment.method = (
        int(fincode_response.get("method", payment.method))
        if fincode_response.get("method") is not None
        else payment.method
    )

    payment.access_id = fincode_response.get("access_id", payment.access_id)
    payment.status = fincode_response.get("status", payment.status)
    payment.process_date = _parse_fincode_process_date(
        fincode_response.get("process_date", payment.process_date)
    )
    payment.error_code = fincode_response.get("error_code", payment.error_code)
    # payment.error_message = fincode_response.get("error_message", payment.error_message)

    payment.tds2_ret_url = fincode_response.get("tds2_ret_url", payment.tds2_ret_url)
    payment.tds2_status = fincode_response.get("tds2_status", payment.tds2_status)
    payment.return_url = fincode_response.get("return_url", payment.return_url)
    payment.return_url_on_failure = fincode_response.get(
        "return_url_on_failure", payment.return_url_on_failure
    )
    # payment.redirect_url = fincode_response.get("redirect_url", payment.redirect_url)
    payment.updated = get_current_time()

    db.add(payment)
    db.commit()
    db.refresh(payment)

    return payment


def _parse_fincode_process_date(process_date_str, default_value=None):
    """
    Parse a datetime string from Fincode in the format 'YYYY/MM/DD HH:MM:SS.mmm'
    and subtract 9 hours. Return the result as a string in the same format
    'YYYY/MM/DD HH:MM:SS.mmm'. If the string is invalid, return the default value.
    """
    if not process_date_str:
        return default_value

    try:
        parsed_date = datetime.strptime(
            process_date_str.strip(), "%Y/%m/%d %H:%M:%S.%f"
        )
        adjusted_date = parsed_date - timedelta(hours=9)
        return adjusted_date.strftime("%Y/%m/%d %H:%M:%S.%f")[
            :-3
        ]  # keep exactly 3 milliseconds digits
    except (ValueError, TypeError):
        return default_value


def get_newest_payment(db: Session, order_number: str) -> Optional[Payment]:
    stmt = (
        select(Payment)
        .where(Payment.order_id == order_number)
        .order_by(Payment.created.desc())
        .limit(1)
    )
    return db.exec(stmt).first()


def get_user_fincode_by_id(db: Session, user_id: str):
    statement = select(UserFincode).where(UserFincode.user_id == user_id)
    return db.exec(statement).first()


def get_card_list(db: Session, user_id: str):
    """Get list of cards for a user and return count and list"""
    statement = select(Card).where(Card.user_id == user_id)
    cards = db.exec(statement).all()
    return len(cards), cards
