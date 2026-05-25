from typing import Optional
from fastapi import APIRouter, Depends, BackgroundTasks, Request
from sqlmodel import Session

from apps.core.database import get_session
from apps.core.schemas import SuccessResponse, ListResponse
from apps.auth.permissions import CustomerUser, AuthenticatedUser
from apps.orders import crud, services
from apps.orders.schemas import OrderCreate, OrderResponse, FincodeWebhookPayload, PickupRequest, LockerSimLookupRequest

router = APIRouter(prefix="/orders", tags=["Заказы"])


@router.post("", response_model=SuccessResponse[OrderResponse], status_code=201)
def create_order(body: OrderCreate, current_user: CustomerUser, db: Session = Depends(get_session)):
    order = services.create_order(db, current_user.id, body.combo_id)
    return SuccessResponse(data=order, message="Заказ создан. Выполните оплату.")


@router.get("", response_model=ListResponse[OrderResponse])
def list_orders(
    year: Optional[int] = None,
    month: Optional[int] = None,
    current_user: AuthenticatedUser = ...,
    db: Session = Depends(get_session),
):
    orders = crud.get_orders_by_customer(db, current_user.id, year=year, month=month)
    return ListResponse(data=orders, total=len(orders))


@router.get("/{order_id}", response_model=SuccessResponse[OrderResponse])
def get_order(order_id: str, current_user: AuthenticatedUser, db: Session = Depends(get_session)):
    order = services.get_order_or_404(db, order_id, current_user.id)
    return SuccessResponse(data=order)


@router.post("/{order_id}/pickup", response_model=SuccessResponse[OrderResponse])
def pickup_order(order_id: str, body: PickupRequest, current_user: CustomerUser, db: Session = Depends(get_session)):
    order = services.pickup_order(db, order_id, current_user.id, body.access_code)
    return SuccessResponse(data=order, message="Заказ получен! Спасибо за покупку.")


@router.post("/sim-pickup", response_model=SuccessResponse[OrderResponse])
def locker_sim_pickup(body: LockerSimLookupRequest, current_user: CustomerUser, db: Session = Depends(get_session)):
    """Locker simulator: find order by access code and mark as completed."""
    order = services.pickup_by_code(db, current_user.id, body.access_code)
    return SuccessResponse(data=order, message="Заказ получен! Спасибо за покупку.")


@router.post("/webhook/fincode", include_in_schema=False)
async def fincode_webhook(request: Request, db: Session = Depends(get_session)):
    try:
        payload = await request.json()
    except Exception:
        return {"status": "ignored"}
    payment_id = payload.get("id", "")
    status = payload.get("status", "")
    if status in ("CAPTURED", "AUTHORIZED"):
        order = crud.get_order_by_fincode_payment_id(db, payment_id)
        if order and order.status == "pending":
            services.mark_order_paid(db, order)
    return {"status": "ok"}
