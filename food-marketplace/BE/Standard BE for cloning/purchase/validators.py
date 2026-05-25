from typing import Union

from sqlmodel import Session

from apps.core.constants import PAYMENT_CAPTURED
from apps.integrations.fincode import FincodeApiClient
from apps.orders.crud import get_order_by_number
from apps.purchase import crud
from apps.purchase.constants import JOB_CODE_DEFAULT, NUMBER_REGISTED_CARD_LIMIT
from apps.purchase.exceptions import (
    card_registration_limit_exceeded,
    invalid_card_owner,
    invalid_order_information,
    user_already_registered,
)
from apps.purchase.models.payments import Payment
from apps.purchase.schemas import PaymentChangeRequest, PaymentRequest
from apps.users.models import User


def check_card_service(db: Session, customer_id: str, card_id: str) -> bool:
    card = crud.get_card_by_customer_id(db, customer_id)
    if card and card.card_id == card_id and card.user_id == customer_id:
        return True
    return False


def check_payment_service(db: Session, customer_id: str, order_id: str) -> bool:
    payment = crud.get_payment_by_order_id(db, order_id)
    if payment and payment.customer_id == customer_id and payment.order_id == order_id:
        return True
    return False


def check_customer_exist(db: Session, customer_id: str):
    return crud.get_user_fincode_by_id(db, customer_id)


def validate_customer_exist(db: Session, user: User):
    if crud.get_user_fincode_by_id(db, user.id):
        raise user_already_registered()


def validate_order_information(
    db: Session,
    request: Union[PaymentRequest, PaymentChangeRequest],
    fincode_service: FincodeApiClient,
):
    order = get_order_by_number(db, request.order_number)
    if (
        not order
        or order.user_id != request.user_id
        or order.shop_id != request.shop_id
    ):
        raise invalid_order_information()


def validate_card_owner(
    customer_id: str, card_id: str, fincode_service: FincodeApiClient
):
    card_list = fincode_service.get_customer_cards(customer_id)
    exists = any(card["id"] == card_id for card in card_list["list"])
    if not exists:
        raise invalid_card_owner()


def validate_registered_card_limit(db: Session, user: User):
    number_registered_card, list_card = crud.get_card_list(db, user.id)
    if number_registered_card > NUMBER_REGISTED_CARD_LIMIT:
        raise card_registration_limit_exceeded()


def validate_payment_change(payment: Payment):
    if (
        not payment
        or payment.status != PAYMENT_CAPTURED
        or payment.job_code != JOB_CODE_DEFAULT
    ):
        raise invalid_order_information()
