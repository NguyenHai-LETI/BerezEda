import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlmodel import Session

from apps.auth.permissions import CustomerUser
from apps.core.database import get_session
from apps.core.logging import logger
from apps.core.schemas import SuccessResponse
from apps.integrations.fincode import FincodeApiClient
from apps.integrations.firebase.client import get_firestore_client
from apps.purchase import schemas, services
from apps.purchase.constants import (
    CAPTURE_SUCCESS_INFORMATION,
    ERROR_HTML,
    FINCODE_WEBHOOK_SIGNATURE,
    PAYMENT_SUCCESS_INFORMATION,
)
from apps.purchase.exceptions import executed_payment_not_found
from apps.purchase.services import get_fincode_service
from apps.purchase.validators import check_card_service, check_payment_service

router = APIRouter(tags=["Purchase"])
callback_router = APIRouter(tags=["Purchase-callbacks"])


@router.post("/customers/register", response_model=SuccessResponse)
def _register_customer(
    user: CustomerUser,
    fincode_service: FincodeApiClient = Depends(get_fincode_service),
    db: Session = Depends(get_session),
):
    """
    This API only using for test, never using for call
    Registration new customer executed automatically
    when API register new card is called
    """
    services._register_new_customer_service(
        fincode_service=fincode_service, db=db, user=user
    )
    return SuccessResponse(data=None)


@router.post("/card/register", response_model=SuccessResponse)
def register_card(
    user: CustomerUser,
    fincode_service: FincodeApiClient = Depends(get_fincode_service),
    db: Session = Depends(get_session),
):
    result = services.register_new_card_service(
        fincode_service=fincode_service, db=db, user=user
    )
    return SuccessResponse(data=result)


@router.get("/cards/list", response_model=SuccessResponse)
def get_user_cards(
    user: CustomerUser,
    fincode_service: FincodeApiClient = Depends(get_fincode_service),
    db: Session = Depends(get_session),
):
    result = services.get_user_cards_service(
        db=db, fincode_service=fincode_service, user=user
    )
    return SuccessResponse(data=result)


@router.post("/cards/set-default/{card_id}", response_model=SuccessResponse)
def set_default_card(
    user: CustomerUser,
    card_id: str,
    fincode_service: FincodeApiClient = Depends(get_fincode_service),
):
    services.set_default_card_service(
        fincode_service=fincode_service, user=user, card_id=card_id
    )
    return SuccessResponse(data=None)


@router.delete("/card/delete/{card_id}", response_model=SuccessResponse)
def delete_card(
    user: CustomerUser,
    card_id: str,
    fincode_service: FincodeApiClient = Depends(get_fincode_service),
    db: Session = Depends(get_session),
):
    services.delete_card_service(
        fincode_service=fincode_service, db=db, user=user, card_id=card_id
    )
    return SuccessResponse(data=None)


@router.post("/payment", response_model=SuccessResponse)
def payment_execute(
    payment_request: schemas.PaymentRequest,
    user: CustomerUser,
    fincode_service: FincodeApiClient = Depends(get_fincode_service),
    db: Session = Depends(get_session),
):
    services.payment_making_service(
        fincode_service=fincode_service,
        db=db,
        user=user,
        payment_request=payment_request,
    )
    return SuccessResponse(data={"information": PAYMENT_SUCCESS_INFORMATION})


@router.post("/payment/change", response_model=SuccessResponse)
def payment_change(
    payment_request: schemas.PaymentChangeRequest,
    user: CustomerUser,
    fincode_service: FincodeApiClient = Depends(get_fincode_service),
    db: Session = Depends(get_session),
):
    services.payment_change_service(
        fincode_service=fincode_service,
        db=db,
        payment_request=payment_request,
    )
    return SuccessResponse(data={"information": CAPTURE_SUCCESS_INFORMATION})


@callback_router.post("/webhook/card-registration")
async def card_registration_success(
    request: Request, db: Session = Depends(get_session)
):
    body = await request.body()
    signature = request.headers.get("fincode-signature")

    logger.info(
        "Card registration webhook received",
        extra={
            "webhook_body": body.decode("utf-8") if body else "",
            "signature_present": bool(signature),
            "endpoint": "card-registration",
        },
    )
    if signature == FINCODE_WEBHOOK_SIGNATURE:
        data = json.loads(body)
        customer_id = data.get("customer_id")
        card_id = data.get("card_id")
        data.get("id")

        # Sync to Firebase: CardPayments/<user_id> with { card: { id, status: "success" } }
        client = get_firestore_client()
        if client and customer_id and card_id:
            doc_ref = client.collection("CardPayments").document(str(customer_id))
            doc_ref.set({"card": {"id": str(card_id), "status": "success"}}, merge=True)

        if check_card_service(db, customer_id, card_id):
            return JSONResponse(
                content={"receive": "0"}, status_code=200, media_type="application/json"
            )

        services.create_card_service(db, customer_id, card_id)
        return JSONResponse(
            content={"receive": "0"}, status_code=200, media_type="application/json"
        )


@callback_router.post("/webhook/payment-execute")
async def payment_success(request: Request, db: Session = Depends(get_session)):

    body = await request.body()
    signature = request.headers.get("fincode-signature")

    if not signature:
        logger.warning("Missing fincode-signature header")
        return JSONResponse(
            status_code=400, content={"detail": "Missing fincode-signature header"}
        )

    if signature == FINCODE_WEBHOOK_SIGNATURE:
        data = json.loads(body)
        order_id = data.get("order_id")
        customer_id = data.get("customer_id")
        if check_payment_service(db, customer_id, order_id):
            return JSONResponse(content={"receive": "0"}, status_code=200)
        else:
            raise executed_payment_not_found()


@callback_router.post("/webhook/3d-secure")
async def payment_3d_secure_success(
    request: Request, db: Session = Depends(get_session)
):
    try:
        body = await request.body()
        signature = request.headers.get("fincode-signature")

        if not signature:
            logger.warning("Missing fincode-signature header")
            return JSONResponse(
                status_code=400,
                content={"detail": "Missing fincode-signature header"},
            )

        if signature == FINCODE_WEBHOOK_SIGNATURE:
            data = json.loads(body)
            logger.warning(f"Body: {data}")
            return JSONResponse(content={"receive": "0"}, status_code=200)

    except Exception as e:
        logger.warning(f"error{e}")
        return HTMLResponse(content=ERROR_HTML.format(error=str(e)), status_code=500)
