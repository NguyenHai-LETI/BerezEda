from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlmodel import Session
from typing import Optional

from apps.core.database import get_session
from apps.core.schemas import SuccessResponse, ListResponse
from apps.auth.permissions import CustomerUser
from apps.payments import crud, services
from apps.payments.schemas import (
    CardResponse,
    CardSessionResponse,
    PaymentRequest,
    PaymentResponse,
    FincodeCustomerResponse,
    UserCardInfo,
)
from apps.core.config import FINCODE_WEBHOOK_SECRET

# ── Purchase endpoints (/purchase prefix set in main.py) ─────────────────────
router = APIRouter(prefix="/purchase", tags=["Purchase / Fincode"])


@router.post("/customers/register", response_model=SuccessResponse[FincodeCustomerResponse])
def register_fincode_customer(current_user: CustomerUser, db: Session = Depends(get_session)):
    """
    Register the current user with Fincode as a customer.
    Idempotent — safe to call even if already registered.
    """
    fc_id = services.ensure_fincode_customer(db, current_user.id, current_user.email)
    return SuccessResponse(data=FincodeCustomerResponse(fincode_customer_id=fc_id))


@router.post("/card/register", response_model=SuccessResponse[CardSessionResponse])
def register_card(current_user: CustomerUser, db: Session = Depends(get_session), combo_id: str = ""):
    """
    Create a Fincode card registration session.
    Returns card_registration_url — frontend opens this in browser/webview.
    After user submits card info, Fincode redirects to success_url (includes combo_id).
    """
    user_name = f"{getattr(current_user, 'first_name', '')} {getattr(current_user, 'last_name', '')}".strip()
    link_url = services.create_card_session(db, current_user.id, current_user.email, user_name, combo_id)
    return SuccessResponse(data=CardSessionResponse(card_registration_url=link_url))


@router.get("/cards/list", response_model=SuccessResponse)
def list_cards(current_user: CustomerUser, db: Session = Depends(get_session)):
    """List all cards for the current user (fetched from Fincode API)."""
    cards = services.get_user_cards(db, current_user.id, current_user.email)
    return SuccessResponse(data=cards)


@router.post("/cards/set-default/{card_id}", response_model=SuccessResponse)
def set_default_card(card_id: str, current_user: CustomerUser):
    """Set a card as the default payment card via Fincode API."""
    services.set_default_card_fincode(current_user.id, card_id)
    return SuccessResponse(message="Default card updated")


@router.delete("/card/delete/{card_id}", response_model=SuccessResponse)
def delete_card(card_id: str, current_user: CustomerUser, db: Session = Depends(get_session)):
    """Delete a card from Fincode and local DB."""
    services.delete_card_fincode(db, current_user.id, card_id)
    return SuccessResponse(message="Card deleted")


@router.post("/payment", response_model=SuccessResponse[PaymentResponse])
def execute_payment(body: PaymentRequest, current_user: CustomerUser, db: Session = Depends(get_session)):
    """
    Execute full 2-step payment:
      1. Register payment intent with Fincode
      2. Execute payment using selected card
    Marks Order as paid on success.
    """
    result = services.execute_full_payment(db, body.order_id, current_user.id, body.card_id)
    # Fetch saved Payment record to return proper schema
    payment = crud.get_payment_by_fincode_id(db, body.order_id)
    return SuccessResponse(data=payment, message="Payment successful")


# ── Webhook callbacks (/purchase-callbacks/webhook prefix set in main.py) ────
webhook_router = APIRouter(prefix="/purchase-callbacks/webhook", tags=["Fincode Webhooks"])


def _verify_signature(fincode_signature: Optional[str]) -> None:
    if FINCODE_WEBHOOK_SECRET and fincode_signature != FINCODE_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook signature")


@webhook_router.post("/card-registration")
async def webhook_card_registration(
    request: Request,
    fincode_signature: Optional[str] = Header(None, alias="fincode-signature"),
    db: Session = Depends(get_session),
):
    """
    Fincode calls this after a user completes card registration via card session link.
    Saves the card to local DB.
    """
    _verify_signature(fincode_signature)
    try:
        payload = await request.json()
    except Exception:
        return {"receive": "0"}

    customer_id = payload.get("customer_id", "")
    card_id = payload.get("card_id", "")

    if customer_id and card_id:
        try:
            services.save_card_from_webhook(db, customer_id, card_id)
        except Exception:
            pass  # best-effort

    return {"receive": "0"}


@webhook_router.post("/payment-execute")
async def webhook_payment_execute(
    request: Request,
    fincode_signature: Optional[str] = Header(None, alias="fincode-signature"),
    db: Session = Depends(get_session),
):
    """
    Fincode calls this after a payment execution (async confirmation).
    Validates the payment record exists.
    """
    _verify_signature(fincode_signature)
    try:
        payload = await request.json()
    except Exception:
        return {"receive": "0"}

    order_id = payload.get("order_id", "")
    status = payload.get("status", "")

    if order_id and status in ("CAPTURED", "AUTHENTICATED"):
        from apps.orders.crud import get_order_by_id
        from apps.orders.services import mark_order_paid
        order = get_order_by_id(db, order_id)
        if order and order.status == "pending":
            try:
                mark_order_paid(db, order)
            except Exception:
                pass

    return {"receive": "0"}


@webhook_router.post("/3d-secure")
async def webhook_3d_secure(
    request: Request,
    fincode_signature: Optional[str] = Header(None, alias="fincode-signature"),
    db: Session = Depends(get_session),
):
    """Handles 3D Secure authentication callbacks from Fincode."""
    _verify_signature(fincode_signature)
    try:
        payload = await request.json()
    except Exception:
        return {"receive": "0"}

    order_id = payload.get("order_id", "")
    if order_id:
        payment = crud.get_payment_by_fincode_id(db, order_id)
        if payment:
            crud.update_payment(db, payment, {"status": "AUTHENTICATED"})

    return {"receive": "0"}
