import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from apps.core.config import SYSTEM1_URL
from apps.core.database import get_session
from apps.core.schemas import SuccessResponse
from apps.locker_codes import crud
from apps.locker_codes.schemas import (
    LockerCodeResponse,
    RegisterDepositRequest,
    RegisterPickupRequest,
    SimulateActionRequest,
    SimulateActionResponse,
    ValidateQRRequest,
    ValidateQRResponse,
)

router = APIRouter(prefix="/api", tags=["Locker Codes"])


@router.post("/locker-codes/register-deposit", response_model=SuccessResponse[LockerCodeResponse])
def register_deposit(body: RegisterDepositRequest, db: Session = Depends(get_session)):
    lc = crud.create_deposit_code(db, body.locker_unit_id, body.location_id, body.combo_id)
    return SuccessResponse(
        data=LockerCodeResponse(
            code=lc.code,
            code_type=lc.code_type,
            numeric_part=lc.numeric_part,
            locker_unit_id=lc.locker_unit_id,
            location_id=lc.location_id,
            combo_id=lc.combo_id,
            order_id=lc.order_id,
        ),
        message="Deposit code registered successfully",
    )


@router.post("/locker-codes/register-pickup", response_model=SuccessResponse[LockerCodeResponse])
def register_pickup(body: RegisterPickupRequest, db: Session = Depends(get_session)):
    lc = crud.create_pickup_code(
        db,
        body.locker_unit_id,
        body.location_id,
        body.combo_id,
        body.order_id,
        body.expires_at,
    )
    return SuccessResponse(
        data=LockerCodeResponse(
            code=lc.code,
            code_type=lc.code_type,
            numeric_part=lc.numeric_part,
            locker_unit_id=lc.locker_unit_id,
            location_id=lc.location_id,
            combo_id=lc.combo_id,
            order_id=lc.order_id,
        ),
        message="Pickup code registered successfully",
    )


@router.post("/qr/validate", response_model=ValidateQRResponse)
def validate_qr(body: ValidateQRRequest, db: Session = Depends(get_session)):
    lc = crud.get_active_code(db, body.qr_code)
    if not lc:
        return ValidateQRResponse(valid=False, message="QR code không hợp lệ hoặc đã hết hạn")
    return ValidateQRResponse(
        valid=True,
        code_type=lc.code_type,
        locker_unit_id=lc.locker_unit_id,
        location_id=lc.location_id,
        combo_id=lc.combo_id,
        order_id=lc.order_id,
        code=lc.code,
        message="QR code hợp lệ",
    )


@router.post("/simulate/deposit-confirmed", response_model=SimulateActionResponse)
def deposit_confirmed(body: SimulateActionRequest, db: Session = Depends(get_session)):
    lc = crud.get_active_code(db, body.code)
    if not lc or lc.code_type != "AA":
        raise HTTPException(status_code=400, detail="Mã nạp hàng không hợp lệ hoặc đã hết hạn")

    try:
        res = httpx.post(
            f"{SYSTEM1_URL}/internal/locker-sim/deposit",
            json={"combo_id": lc.combo_id},
            timeout=10.0,
        )
        res.raise_for_status()
        system1_data = res.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"System 1 trả về lỗi: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Không thể kết nối System 1: {str(e)}")

    crud.mark_code_used(db, lc)
    return SimulateActionResponse(
        success=True,
        message="Đã nạp hàng vào tủ. Combo đang được bán.",
        system1_response=system1_data,
    )


@router.post("/simulate/pickup-confirmed", response_model=SimulateActionResponse)
def pickup_confirmed(body: SimulateActionRequest, db: Session = Depends(get_session)):
    lc = crud.get_active_code(db, body.code)
    if not lc or lc.code_type != "BB":
        raise HTTPException(status_code=400, detail="Mã lấy hàng không hợp lệ hoặc đã hết hạn")

    try:
        res = httpx.post(
            f"{SYSTEM1_URL}/internal/locker-sim/pickup",
            json={"order_id": lc.order_id},
            timeout=10.0,
        )
        res.raise_for_status()
        system1_data = res.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"System 1 trả về lỗi: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Không thể kết nối System 1: {str(e)}")

    crud.mark_code_used(db, lc)
    return SimulateActionResponse(
        success=True,
        message="Đã lấy hàng thành công. Đơn hàng hoàn tất.",
        system1_response=system1_data,
    )
