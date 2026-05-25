"""
Order API Endpoints
"""

import json
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlmodel import Session

from apps.auth.permissions import AdminUser, AuthenticatedUser, CustomerUser
from apps.core.database import get_session
from apps.core.schemas import ErrorResponse, ListResponse, SuccessResponse
from apps.integrations.fincode.api_client import FincodeApiClient
from apps.purchase.services import get_fincode_service

from . import schemas, services

router = APIRouter(tags=["Orders"])


@router.post("/", response_model=SuccessResponse[schemas.OrderRead])
def buy_combo(
    order_data: schemas.OrderCreate,
    user: CustomerUser,
    db: Session = Depends(get_session),
    fincode_service: FincodeApiClient = Depends(get_fincode_service),
):
    """
    Buy a combo - creates an order with card payment via Fincode
    """
    order = services.buy_combo_service(order_data, user, db, fincode_service)
    return SuccessResponse(data=order)


@router.get("/", response_model=ListResponse[schemas.OrderRead])
def get_my_orders(
    user: AuthenticatedUser,
    db: Session = Depends(get_session),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None, description="Filter by order status"),
    pickup_month: Optional[str] = Query(
        None, description="Filter by pickup month in YYYY-MM format"
    ),
):
    orders, total = services.get_user_orders_service(
        user, db, limit, offset, status, pickup_month
    )
    return ListResponse(limit=limit, offset=offset, total=total, data=orders)


# @router.get("/{order_id}", response_model=SuccessResponse[schemas.OrderRead])
# def get_order(
#     order_id: str,
#     user: AuthenticatedUser,
#     db: Session = Depends(get_session),
# ):
#     """
#     Get specific order details
#     """
#     order = services.get_order_service(order_id, user, db)
#     return SuccessResponse(data=order)


@router.get("/{order_id}", response_model=SuccessResponse[schemas.OrderDetailRead])
def get_order_details(
    order_id: str,
    user: AuthenticatedUser,
    db: Session = Depends(get_session),
):
    """
    Get enhanced order details with shop, combo, and locker information
    """
    order = services.get_order_detail_service(order_id, user, db)
    return SuccessResponse(data=order)


@router.post("/{order_id}/pickup", response_model=SuccessResponse[schemas.OrderRead])
def confirm_pickup(
    order_id: str,
    user: AuthenticatedUser,
    pickup_code: str = Query(..., description="6-digit pickup code"),
    db: Session = Depends(get_session),
):
    """
    Confirm order pickup with pickup code
    """
    order = services.confirm_pickup_service(order_id, pickup_code, db)
    return SuccessResponse(data=order)


@router.post("/{order_id}/cancel", response_model=SuccessResponse[schemas.OrderRead])
def cancel_order(
    order_id: str,
    user: AuthenticatedUser,
    db: Session = Depends(get_session),
    fincode_service: FincodeApiClient = Depends(get_fincode_service),
):
    """
    Cancel an order (if allowed)
    """
    # order = services.cancel_order_service(order_id, user, db, fincode_service)
    return ErrorResponse(
        message="この機能は削除されました。最新バージョンをダウンロードしてください。"
    )


@router.put(
    "/{order_id}/admin-refund",
    response_model=SuccessResponse[schemas.OrderRead],
)
def admin_refund_order(
    order_id: str,
    user: AdminUser,
    db: Session = Depends(get_session),
    fincode_service: FincodeApiClient = Depends(get_fincode_service),
):
    """
    [Admin only] Cancel payment (full refund) via Fincode and set order to cancelled.
    Use when there are operational issues and the customer claims a refund.
    """
    order = services.admin_refund_order_service(
        order_id=order_id,
        db=db,
        fincode_service=fincode_service,
    )
    return SuccessResponse(data=order)


# Create a separate router for webhooks (no authentication needed)
webhook_router = APIRouter(tags=["Order Webhooks"])


@webhook_router.post("/payment-webhook")
async def handle_payment_webhook(
    request: Request,
    db: Session = Depends(get_session),
):
    """
    Handle payment webhook from Fincode
    """
    try:
        body = await request.body()
        data = json.loads(body)

        # Extract payment information from webhook
        order_id = data.get("order_id")
        # payment_status = data.get("status")
        transaction_id = data.get("access_id")

        if order_id:  # and payment_status:
            result = services.handle_payment_webhook_service(
                order_id=order_id,
                transaction_id=transaction_id,
                db=db,
            )

            if result:
                return JSONResponse(content={"success": True}, status_code=200)

        return JSONResponse(content={"success": False}, status_code=400)

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
