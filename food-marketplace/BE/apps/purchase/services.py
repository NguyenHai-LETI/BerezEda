import math
from datetime import datetime

from fastapi import HTTPException, status
from sqlmodel import Session

from apps.core.constants import PAYMENT_CAPTURED, PAYMENT_INIT, PAYMENT_UNPROCESSED
from apps.core.utils import get_current_time
from apps.integrations.branchio import create_branchio_deeplink
from apps.integrations.branchio.deeplink import create_deeplink_data
from apps.integrations.fincode.api_client import FincodeApiClient
from apps.purchase import crud
from apps.purchase.constants import REFUND_PENALTY_PERCENTAGE
from apps.purchase.exceptions import payment_already_success_making
from apps.purchase.models import Payment
from apps.purchase.models.users_fincode import Card, UserFincode
from apps.purchase.schemas import (
    FincodeCardSessionRequest,
    FincodeCustomerCreateRequest,
    PaymentCancelFincodeRequest,
    PaymentChangeFincodeRequest,
    PaymentChangeRequest,
    PaymentCreateFincodeRequest,
    PaymentExecuteFincodeRequest,
    PaymentRequest,
    UserCardInfo,
)
from apps.purchase.validators import (
    check_customer_exist,
    validate_card_owner,
    validate_customer_exist,
    validate_order_information,
    validate_payment_change,
    validate_registered_card_limit,
)
from apps.users.models import User


def get_fincode_service():
    service = FincodeApiClient()
    try:
        yield service
    finally:
        service.close()


def _register_new_customer_service(
    fincode_service: FincodeApiClient,
    db: Session,
    user: User,
):
    validate_customer_exist(db, user)

    if user.name is not None:
        fincode_name = user.name
    elif user.username is not None:
        fincode_name = user.username
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must have at least a name or a username.",
        )
    user_fincode = FincodeCustomerCreateRequest(
        id=user.id, email=user.email, name=fincode_name
    )

    result = fincode_service.register_new_customer(user_fincode)
    if not result:
        raise ValueError("Failed to register new customer: result is None")
    user_fincode = UserFincode(
        user_id=result["id"],
        card_registration=result.get("card_registration"),
        directdebit_registration=result.get("directdebit_registration"),
        created=datetime.strptime(result["created"], "%Y/%m/%d %H:%M:%S.%f"),
        updated=datetime.strptime(result["updated"], "%Y/%m/%d %H:%M:%S.%f"),
    )
    crud.create_user_fincode(db, user_fincode)
    return result


def register_new_card_service(
    fincode_service: FincodeApiClient, db: Session, user: User
):
    if not check_customer_exist(db, user.id):
        _register_new_customer_service(fincode_service, db, user)

    validate_registered_card_limit(db, user)

    success_url, failure_url = _create_shortlinks_card_register(user.id)
    card_session_request = FincodeCardSessionRequest(
        customer_id=user.id,
        customer_name=user.name or "",
        tds_type="0",
        tds2_type="0",
        success_url=success_url,
        cancel_url=failure_url,
    )

    result = fincode_service.register_new_card(card_session_request)
    response = {"card_registration_url": result.get("link_url")}
    return response


def _create_shortlinks_card_register(user_id: str):
    original_success_path = f"?customer_id={user_id}&success=True"
    original_failure_path = f"?customer_id={user_id}&success=Flase"
    param_data_success = {"customer_id": user_id, "status": "Success"}
    param_data_failure = {"customer_id": user_id, "status": "Failed"}
    success_data = create_deeplink_data(
        original_success_path, name_feature="card_registration", data=param_data_success
    )
    failure_data = create_deeplink_data(
        original_failure_path, name_feature="card_registration", data=param_data_failure
    )
    success_url = create_branchio_deeplink(success_data)
    failure_url = create_branchio_deeplink(failure_data)
    return success_url, failure_url


def delete_card_service(
    fincode_service: FincodeApiClient, db: Session, user: User, card_id: str
):
    result = fincode_service.delete_card(user.id, card_id)
    crud.delete_card(db, user.id, card_id)
    return result


def get_user_cards_service(fincode_service: FincodeApiClient, user: User, db: Session):

    if not check_customer_exist(db, user.id):
        _register_new_customer_service(fincode_service, db, user)

    result = fincode_service.get_customer_cards(user.id)
    card_list = []
    for item in result.get("list", []):
        expired_time = item.get("expire", "")
        yy = expired_time[:2]
        mm = expired_time[2:]
        expire = f"{yy}/{mm}"
        user_card = UserCardInfo(
            card_id=item["id"],
            brand=item.get("brand", ""),
            card_no=item.get("card_no", ""),
            expire=expire,
            holder_name=item.get("holder_name", ""),
            is_default=True if item.get("default_flag", "") == "1" else False,
        )
        card_list.append(user_card)

    return {"cards": card_list}


def set_default_card_service(
    fincode_service: FincodeApiClient, user: User, card_id: str
):
    result = fincode_service.set_default_card(user.id, card_id)
    return result


def payment_making_service(
    fincode_service: FincodeApiClient,
    db: Session,
    user: User,
    payment_request: PaymentRequest,
):
    validate_order_information(db, payment_request, fincode_service)
    validate_card_owner(
        payment_request.user_id, payment_request.card_id, fincode_service
    )
    payment = crud.get_newest_payment(db, payment_request.order_number)

    if not payment or payment.status == PAYMENT_INIT:
        init_payment = Payment(
            amount=0, status=PAYMENT_INIT, order_id=payment_request.order_number
        )
        payment = crud.create_payment(db, init_payment)
        registration_response = payment_registration_service(
            fincode_service, payment_request
        )
        payment = crud.update_payment(db, payment.id, registration_response)

    if payment.status == PAYMENT_UNPROCESSED:
        payment = _create_copy_payment_service(db, payment)
        payment_execution_response = payment_execution_service(
            fincode_service, payment_request, payment.access_id
        )
        # TODO: catch error when fail payment, update error status to payment record
        crud.update_payment(db, payment.id, payment_execution_response)
    else:
        raise payment_already_success_making()
    return payment_execution_response


def _create_copy_payment_service(db: Session, payment: Payment):
    payment_data = payment.model_dump()
    payment_data.pop("id", None)
    payment_data["created"] = get_current_time()
    payment_data["updated"] = get_current_time()
    new_payment = Payment(**payment_data)
    return crud.create_payment(db, new_payment)


def payment_registration_service(
    fincode_service: FincodeApiClient,
    payment_request: PaymentRequest,
):
    payment_registration_request = PaymentCreateFincodeRequest(
        id=payment_request.order_number,
        amount=payment_request.amount,
        client_field_1=payment_request.shop_id,
        # TODO: bật xác thực 3D
        tds_type="0",
        tds2_type="2",
    )
    return fincode_service.payment_registration(payment_registration_request)


def payment_execution_service(
    fincode_service: FincodeApiClient, payment_request: PaymentRequest, access_id: str
):
    payment_execution_request = PaymentExecuteFincodeRequest(
        access_id=access_id,
        customer_id=payment_request.user_id,
        card_id=payment_request.card_id,
    )
    return fincode_service.payment_execution(
        payment_request.order_number, payment_execution_request
    )


def payment_change_service(
    fincode_service: FincodeApiClient,
    db: Session,
    payment_request: PaymentChangeRequest,
):
    validate_order_information(db, payment_request, fincode_service)
    payment = crud.get_newest_payment(db, payment_request.order_number)
    validate_payment_change(payment)
    payment = _create_copy_payment_service(db, payment)
    payment_change_request = PaymentChangeFincodeRequest(
        access_id=payment.access_id,
        amount=str(math.ceil(payment.amount * REFUND_PENALTY_PERCENTAGE)),
    )
    payment_change_response = fincode_service.payment_change(
        payment_request.order_number, payment_change_request
    )
    if payment_change_response:
        # TODO: change status ?
        payment_change_response["status"] = PAYMENT_CAPTURED
        crud.update_payment(db, payment.id, payment_change_response)
    return payment_change_response


def payment_cancel_service(
    fincode_service: FincodeApiClient,
    db: Session,
    order_id: str,
):
    """
    Cancel (full refund) a captured payment via Fincode.
    order_id: our Order.id (UUID). Resolves to order_number -> payment.
    Used by admin to refund customer when cancelling due to operational issues.
    """
    from apps.orders.crud import get_order_by_id

    order = get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )
    payment = crud.get_newest_payment(db, order.order_number)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found for this order",
        )
    if payment.status != PAYMENT_CAPTURED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment is not captured (status={payment.status}). Only captured payments can be cancelled.",
        )
    if not payment.access_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment has no access_id, cannot cancel via Fincode",
        )
    cancel_request = PaymentCancelFincodeRequest(
        pay_type="Card",
        access_id=payment.access_id,
    )
    # Fincode: id in URL = payments.order_id (our order_number)
    response = fincode_service.payment_cancel(payment.order_id, cancel_request)
    if response:
        crud.update_payment(db, payment.id, response)
    return response


def create_card_service(db: Session, customer_id: str, card_id: str):
    card = Card(user_id=customer_id, card_id=card_id)
    crud.create_card(db, card)
