from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from apps.auth.permissions import AdminUser, AuthenticatedUser
from apps.core.database import get_session
from apps.core.schemas import ListResponse, SuccessResponse

from .schemas import (
    QrcodeGenerateRequest,
    QrcodeGenerateResponse,
    QrcodeRead,
    QrcodeVerifyRequest,
)
from .services import (
    delete_qrcode_service,
    generate_qrcodes_service,
    get_qrcode_service,
    list_qrcodes_service,
    verify_qrcode_service,
)

router = APIRouter(tags=["QR Codes"])


@router.get("/", response_model=ListResponse[QrcodeRead])
def list_qrcodes(
    user: AdminUser,
    db: Session = Depends(get_session),
    is_used: Optional[bool] = Query(False, description="Filter by usage status"),
    is_active: Optional[bool] = Query(True, description="Filter by active status"),
    limit: int = Query(21, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    total, qrcodes = list_qrcodes_service(
        db,
        is_used=is_used,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )
    return ListResponse(data=qrcodes, total=total, limit=limit, offset=offset)


@router.get("/{qrcode_id}", response_model=SuccessResponse[QrcodeRead])
def get_qrcode(
    user: AdminUser,
    qrcode_id: str,
    db: Session = Depends(get_session),
):
    qrcode = get_qrcode_service(qrcode_id, db)
    return SuccessResponse(data=qrcode)


@router.post(
    "/generate",
    response_model=SuccessResponse[QrcodeGenerateResponse],
    status_code=status.HTTP_201_CREATED,
)
def generate_qrcodes(
    user: AdminUser,
    request: QrcodeGenerateRequest,
    db: Session = Depends(get_session),
):
    generated_qrcodes = generate_qrcodes_service(request, db)
    return SuccessResponse(data=generated_qrcodes)


@router.post(
    "/verify",
    response_model=SuccessResponse[QrcodeRead],
)
def verify_qrcode(
    user: AuthenticatedUser,
    request: QrcodeVerifyRequest,
    db: Session = Depends(get_session),
):
    verified_qrcode = verify_qrcode_service(request, user.id, db)
    return SuccessResponse(data=verified_qrcode)


@router.delete("/{qrcode_id}", response_model=SuccessResponse[dict])
def delete_qrcode(
    user: AuthenticatedUser,
    qrcode_id: str,
    db: Session = Depends(get_session),
):
    result = delete_qrcode_service(qrcode_id, db)
    return SuccessResponse()
