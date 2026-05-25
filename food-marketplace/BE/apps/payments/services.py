from fastapi import HTTPException
from sqlmodel import Session

from apps.payments import crud
from apps.integrations.fincode_client import fincode_client

CARD_LIMIT = 4  # max cards per user


# ── Customer registration ────────────────────────────────────────────────────

def ensure_fincode_customer(db: Session, user_id: str, email: str, name: str = "") -> str:
    """
    Get or create a Fincode customer for the user.
    Returns fincode_customer_id.
    Idempotent: safe to call multiple times.
    """
    fu = crud.get_fincode_user(db, user_id)
    if fu:
        return fu.fincode_customer_id

    # Create in Fincode
    try:
        result = fincode_client.create_customer(user_id, email, name)
        fc_id = result.get("id", user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Fincode customer creation failed: {str(e)}")

    crud.create_fincode_user(db, user_id, fc_id)
    return fc_id


# ── List cards from Fincode API ───────────────────────────────────────────────

def get_user_cards(db: Session, user_id: str, email: str) -> list:
    """
    Fetch cards directly from Fincode API (source of truth).
    Auto-registers user with Fincode if not yet registered.
    """
    from apps.payments.schemas import UserCardInfo

    fu = crud.get_fincode_user(db, user_id)
    if not fu:
        ensure_fincode_customer(db, user_id, email)
        fu = crud.get_fincode_user(db, user_id)

    try:
        result = fincode_client.list_cards(fu.fincode_customer_id)
    except Exception:
        result = []

    card_list = []
    for item in result:
        expired_time = item.get("expire", "")
        yy = expired_time[:2]
        mm = expired_time[2:]
        expire = f"{yy}/{mm}" if expired_time else ""
        fincode_card_id = item.get("id", "")
        card_list.append(UserCardInfo(
            id=fincode_card_id,
            fincode_card_id=fincode_card_id,
            card_number_masked=item.get("card_no", "****"),
            brand=item.get("brand", ""),
            expire=expire,
            holder_name=item.get("holder_name", ""),
            is_default=item.get("default_flag", "") == "1",
        ))

    return card_list


# ── Card registration session ────────────────────────────────────────────────

def create_card_session(db: Session, user_id: str, email: str, user_name: str = "", combo_id: str = "") -> str:
    """
    Ensure fincode customer exists, check card limit,
    then create a card registration session.
    Returns the link_url for the user to open in browser.
    """
    if crud.count_cards_by_customer(db, user_id) >= CARD_LIMIT:
        raise HTTPException(status_code=400, detail=f"Card limit reached (max {CARD_LIMIT})")

    fc_id = ensure_fincode_customer(db, user_id, email, user_name)

    try:
        result = fincode_client.create_card_session(fc_id, customer_name=user_name, combo_id=combo_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Card session creation failed: {str(e)}")

    link_url = result.get("link_url", "")
    if not link_url:
        raise HTTPException(status_code=400, detail="Fincode did not return card registration URL")

    return link_url


# ── Card management (Fincode API direct) ─────────────────────────────────────

def set_default_card_fincode(user_id: str, card_id: str) -> None:
    """Set default card via Fincode API (like standard template)."""
    try:
        fincode_client.set_default_card(user_id, card_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to set default card: {str(e)}")


def delete_card_fincode(db: Session, user_id: str, card_id: str) -> None:
    """Delete card from Fincode API and local DB."""
    try:
        fincode_client.delete_card(user_id, card_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to delete card: {str(e)}")
    # Also clean up local DB if exists
    try:
        local_card = crud.get_card_by_fincode_id(db, user_id, card_id)
        if local_card:
            crud.delete_card(db, local_card)
    except Exception:
        pass  # local cleanup is best-effort


def set_default_card(db: Session, user_id: str, card_id: str) -> None:
    card = crud.get_card_by_id(db, card_id)
    if not card or card.customer_id != user_id:
        raise HTTPException(status_code=404, detail="Card not found")

    fu = crud.get_fincode_user(db, user_id)
    if fu:
        try:
            fincode_client.set_default_card(fu.fincode_customer_id, card.fincode_card_id)
        except Exception:
            pass  # local DB update is still applied

    crud.set_card_default(db, user_id, card_id)


def delete_card(db: Session, user_id: str, card_id: str) -> None:
    card = crud.get_card_by_id(db, card_id)
    if not card or card.customer_id != user_id:
        raise HTTPException(status_code=404, detail="Card not found")

    fu = crud.get_fincode_user(db, user_id)
    if fu:
        try:
            fincode_client.delete_card(fu.fincode_customer_id, card.fincode_card_id)
        except Exception:
            pass  # proceed to delete locally even if fincode call fails

    crud.delete_card(db, card)


# ── Webhook: save card after user completes registration ─────────────────────

def save_card_from_webhook(db: Session, customer_id: str, fincode_card_id: str) -> None:
    """
    Called by the card-registration webhook after user successfully registers a card.
    Fetches card details from Fincode and saves to local DB.
    """
    fu = crud.get_fincode_user(db, customer_id)
    if not fu:
        return  # unknown user, ignore

    # Avoid duplicate
    if crud.get_card_by_fincode_id(db, customer_id, fincode_card_id):
        return

    # Fetch card details from Fincode
    try:
        cards = fincode_client.list_cards(fu.fincode_customer_id)
        card_data = next((c for c in cards if c.get("id") == fincode_card_id), None)
    except Exception:
        card_data = None

    if not card_data:
        card_data = {"id": fincode_card_id}

    is_default = card_data.get("default_flag", "0") == "1"

    # If this card is default, clear existing defaults
    if is_default:
        crud.set_card_default(db, customer_id, "")  # clear all first

    crud.create_card(db, {
        "customer_id": customer_id,
        "fincode_customer_id": fu.fincode_customer_id,
        "fincode_card_id": fincode_card_id,
        "card_number_masked": card_data.get("card_no", "****"),
        "brand": card_data.get("brand", ""),
        "expire": card_data.get("expire", ""),
        "holder_name": card_data.get("holder_name", ""),
        "is_default": is_default,
    })


# ── Payment ──────────────────────────────────────────────────────────────────

def execute_full_payment(db: Session, order_id: str, customer_id: str, card_id: str) -> dict:
    """
    Full 2-step Fincode payment:
      1. POST /v1/payments  → register, get access_id
      2. PUT  /v1/payments/{order_id} → execute
    Saves Payment record to DB and marks Order as paid on success.
    """
    from apps.orders.crud import get_order_by_id
    from apps.orders.exceptions import order_not_found, order_access_denied

    order = get_order_by_id(db, order_id)
    if not order:
        raise order_not_found()
    if order.customer_id != customer_id:
        raise order_access_denied()
    if order.status == "paid":
        raise HTTPException(status_code=400, detail="Order is already paid")

    # card_id is a fincode card ID (not local DB ID)
    fc_customer_id = customer_id  # user.id == fincode customer_id
    # Use order_number for Fincode (format: ORD{timestamp}{random})
    fincode_order_id = order.order_number

    # Create Payment record (INIT)
    payment = crud.create_payment(db, {
        "order_id": order_id,
        "customer_id": customer_id,
        "card_id": card_id,
        "fincode_payment_id": fincode_order_id,
        "fincode_customer_id": fc_customer_id,
        "amount": order.amount,
        "status": "INIT",
    })

    # Step 1: Register payment with Fincode (uses order_number as ID)
    try:
        reg_result = fincode_client.register_payment(fincode_order_id, order.amount, order.shop_id)
        access_id = reg_result.get("access_id", "")
    except Exception as e:
        crud.update_payment(db, payment, {"status": "FAILED"})
        raise HTTPException(status_code=400, detail=f"Fincode payment registration failed: {str(e)}")

    crud.update_payment(db, payment, {
        "status": "UNPROCESSED",
        "fincode_access_id": access_id,
    })

    # Step 2: Execute payment (uses order_number as ID)
    try:
        exec_result = fincode_client.execute_payment(fincode_order_id, access_id, fc_customer_id, card_id)
        pay_status = exec_result.get("status", "")
    except Exception as e:
        crud.update_payment(db, payment, {"status": "FAILED"})
        raise HTTPException(status_code=400, detail=f"Fincode payment execution failed: {str(e)}")

    crud.update_payment(db, payment, {"status": pay_status})

    if pay_status in ("CAPTURED", "AUTHENTICATED"):
        from apps.orders.services import mark_order_paid
        mark_order_paid(db, order)
    else:
        error_code = exec_result.get("error_code", "")
        error_msg = exec_result.get("error_message", pay_status)
        raise HTTPException(status_code=400, detail=f"Payment failed ({error_code}): {error_msg}")

    return exec_result
