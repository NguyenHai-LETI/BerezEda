import io
import os
import secrets
import string
import time
from typing import List, Optional

import qrcode
from sqlmodel import Session

from apps.core.utils import get_current_time
from apps.integrations.aws.s3 import upload_file_to_s3
from apps.integrations.branchio.deeplink import (
    create_branchio_deeplink,
    create_deeplink_data,
)
from apps.qrcode import crud
from apps.qrcode.models.qrcode import Qrcode
from apps.users.crud import update_user
from apps.users.models.users import User

from .exceptions import (
    qrcode_already_used,
    qrcode_cannot_delete_used,
    qrcode_inactive,
    qrcode_not_found,
    user_already_verified,
)
from .schemas import (
    QrcodeGenerateRequest,
    QrcodeGenerateResponse,
    QrcodeRead,
    QrcodeVerifyRequest,
)


def _generate_unique_qr_data() -> str:
    timestamp = int(time.time())
    random_string = "".join(
        secrets.choice(string.ascii_letters + string.digits) for _ in range(8)
    )
    return f"QR_{timestamp}_{random_string}"


def _generate_qr_code_image(qr_data: str) -> bytes:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)
    return img_bytes.getvalue()


def get_qrcode_service(qrcode_id: str, db: Session) -> QrcodeRead:
    qrcode = crud.get_qrcode_by_id(db, qrcode_id)
    if not qrcode:
        raise qrcode_not_found()
    return QrcodeRead.model_validate(qrcode, from_attributes=True)


def list_qrcodes_service(
    db: Session,
    is_used: Optional[bool] = None,
    is_active: Optional[bool] = True,
    limit: int = 20,
    offset: int = 0,
) -> tuple[int, List[QrcodeRead]]:
    """List QR codes with optional filtering"""
    qrcodes, total = crud.get_qrcodes(
        db,
        is_used=is_used,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )
    return (
        total,
        [QrcodeRead.model_validate(qrcode, from_attributes=True) for qrcode in qrcodes],
    )


def delete_qrcode_service(qrcode_id: str, db: Session):
    qrcode = crud.get_qrcode_by_id(db, qrcode_id)
    if not qrcode or not qrcode.is_active:
        raise qrcode_not_found()
    if qrcode.is_used:
        raise qrcode_cannot_delete_used()
    crud.delete_qrcode(db, qrcode)
    return None


def generate_qrcodes_service(
    request: QrcodeGenerateRequest, db: Session
) -> QrcodeGenerateResponse:
    """Generate multiple QR codes with original link format and upload images to S3"""
    list_qrcode = []

    for _ in range(request.count):
        qr_data = _generate_unique_qr_data()
        if os.getenv("ENVIRONMENT") == "production":
            original_path = f"v1/qrcodes/verify?qr_data={qr_data}"
        else:
            original_path = f"api/qrcodes/verify?qr_data={qr_data}"
        param_data = {"qr_data": qr_data}
        deeplink_data = create_deeplink_data(
            original_path, name_feature="qrcode", data=param_data
        )
        deeplink_url = create_branchio_deeplink(deeplink_data)

        qrcode = Qrcode(qr_data=qr_data)
        qr_image_bytes = _generate_qr_code_image(deeplink_url)
        file_obj = io.BytesIO(qr_image_bytes)
        filename = f"qrcodes/{qrcode.id}.png"
        s3_url = upload_file_to_s3(file_obj, filename)
        qrcode.image_url = s3_url
        list_qrcode.append(qrcode)

    crud.create_qrcode(db, list_qrcode)
    response_qrcode = [
        QrcodeRead.model_validate(qr, from_attributes=True) for qr in list_qrcode
    ]

    return QrcodeGenerateResponse(
        qrcodes=response_qrcode, total_generated=len(response_qrcode)
    )


def verify_qrcode_service(
    request: QrcodeVerifyRequest, user_id: str, db: Session
) -> QrcodeRead:
    """Verify QR code by data and mark as used, also update user verification status"""
    user = db.get(User, user_id)
    if user and user.is_verification_qrcode:
        raise user_already_verified()

    qrcode = crud.get_qrcode_by_data(db, request.qr_data)
    if not qrcode:
        raise qrcode_not_found()
    if not qrcode.is_active:
        raise qrcode_inactive()
    if qrcode.is_used:
        raise qrcode_already_used()

    user.is_verification_qrcode = True
    user.qrcode_verified_at = get_current_time()
    user.verification_code = request.qr_data
    update_user(db, user)
    verified_qrcode = crud.mark_qrcode_used(db, qrcode, user_id)

    return QrcodeRead.model_validate(verified_qrcode, from_attributes=True)
