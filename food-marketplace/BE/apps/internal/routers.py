"""
Internal endpoints called by the Locker Simulation system (System 2).
These are open (no auth) for the demo — add API key protection later.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from apps.core.database import get_session
from apps.core.schemas import SuccessResponse
from apps.core.utils import utcnow
from apps.combos import crud as combo_crud
from apps.combos.exceptions import combo_not_found
from apps.lockers.services import mark_unit_occupied, mark_unit_available
from apps.integrations.firebase_client import firebase_service

router = APIRouter(prefix="/internal", tags=["Internal — Locker Sim"])


class DepositRequest(BaseModel):
    combo_id: str


class PickupRequest(BaseModel):
    order_id: str


@router.post("/locker-sim/deposit", response_model=SuccessResponse)
def sim_deposit(body: DepositRequest, db: Session = Depends(get_session)):
    """
    Called by System 2 after seller scans AA QR and clicks 'Mô phỏng cho đồ vào'.
    Marks unit as occupied, publishes combo → available (SELLING), syncs Firebase.
    """
    from datetime import timedelta
    from apps.scheduler.scheduler import schedule_combo_expiry

    combo = combo_crud.get_combo_by_id(db, body.combo_id)
    if not combo:
        raise HTTPException(status_code=404, detail="Combo not found")
    if combo.status not in ("ready", "draft"):
        raise HTTPException(
            status_code=400,
            detail=f"Combo is already in status '{combo.status}', cannot deposit",
        )
    if not combo.locker_unit_id:
        raise HTTPException(status_code=400, detail="Combo has no locker unit assigned")

    mark_unit_occupied(db, combo.locker_unit_id)

    now = utcnow()
    combo.status = "available"
    combo.sale_start_time = now
    combo.sale_end_time = now + timedelta(hours=combo.sale_duration_hours)
    combo.updated_at = now
    db.add(combo)
    db.commit()
    db.refresh(combo)

    job_id = schedule_combo_expiry(combo.id, combo.sale_end_time)
    if job_id:
        combo.scheduled_expiry_job_id = job_id
        db.add(combo)
        db.commit()
        db.refresh(combo)

    firebase_service.sync_combo(combo.id, {
        "id": combo.id,
        "shop_id": combo.shop_id,
        "locker_unit_id": combo.locker_unit_id,
        "locker_location_id": combo.locker_location_id,
        "title": combo.title,
        "sale_price": combo.sale_price,
        "status": combo.status,
        "sale_end_time": combo.sale_end_time.isoformat() if combo.sale_end_time else None,
    })

    return SuccessResponse(
        data={"combo_id": combo.id, "status": combo.status},
        message="Combo published — item deposited in locker",
    )


@router.post("/locker-sim/pickup", response_model=SuccessResponse)
def sim_pickup(body: PickupRequest, db: Session = Depends(get_session)):
    """
    Called by System 2 after buyer scans BB QR and clicks 'Mô phỏng lấy đồ ra'.
    Marks unit as available, marks order as completed, syncs Firebase.
    """
    from apps.orders import crud as order_crud
    from apps.combos.crud import mark_combo_sold
    from apps.scheduler.scheduler import cancel_order_expiry

    order = order_crud.get_order_by_id(db, body.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status not in ("paid", "READY_FOR_PICKUP"):
        raise HTTPException(
            status_code=400,
            detail=f"Order is in status '{order.status}', cannot complete pickup",
        )

    cancel_order_expiry(order.id)

    if order.locker_unit_id:
        mark_unit_available(db, order.locker_unit_id)

    combo = combo_crud.get_combo_by_id(db, order.combo_id)
    if combo and combo.status not in ("sold", "completed"):
        mark_combo_sold(db, combo)
        firebase_service.delete_combo(str(combo.id))

    order = order_crud.update_order(db, order, {
        "status": "completed",
        "completed_at": utcnow(),
    })

    return SuccessResponse(
        data={"order_id": order.id, "status": order.status},
        message="Pickup confirmed — order completed",
    )
