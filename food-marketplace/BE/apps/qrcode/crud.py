from datetime import datetime
from typing import List, Optional

from sqlalchemy import func
from sqlmodel import Session, select

from apps.qrcode.models.qrcode import Qrcode
from apps.users.models.users import User

from .exceptions import qrcode_cannot_delete_used


def create_qrcode(db: Session, list_qr_code: List[Qrcode]):
    db.add_all(list_qr_code)
    db.commit()
    for qr_code in list_qr_code:
        db.refresh(qr_code)


def get_qrcode_by_id(db: Session, qrcode_id: str) -> Optional[Qrcode]:
    """Get QR code by ID (only active ones)"""
    query = select(Qrcode).where(Qrcode.id == qrcode_id, Qrcode.is_active == True)
    return db.exec(query).first()


def get_qrcodes(
    db: Session,
    is_used: Optional[bool] = None,
    is_active: Optional[bool] = True,
    limit: int = 20,
    offset: int = 0,
) -> tuple[List[Qrcode], int]:
    """Get QR codes with optional filtering"""
    base_query = select(Qrcode)
    count_query = select(func.count()).select_from(Qrcode)

    # Filter by active status
    if is_active is not None:
        base_query = base_query.where(Qrcode.is_active == is_active)
        count_query = count_query.where(Qrcode.is_active == is_active)

    # Filter by usage status
    if is_used is not None:
        base_query = base_query.where(Qrcode.is_used == is_used)
        count_query = count_query.where(Qrcode.is_used == is_used)

    # Get total count
    total = db.exec(count_query).one()

    # Get paginated qrcodes, ordered by created_at descending (newest first)
    statement = (
        base_query.order_by(Qrcode.created_at.desc()).offset(offset).limit(limit)
    )
    qrcodes = db.exec(statement).all()

    return list(qrcodes), total


def delete_qrcode(db: Session, qrcode: Qrcode):
    qrcode.is_active = False
    db.commit()
    db.refresh(qrcode)


def get_qrcode_by_data(db: Session, qr_data: str) -> Optional[Qrcode]:
    """Get QR code by QR data (only active ones)"""
    query = select(Qrcode).where(Qrcode.qr_data == qr_data, Qrcode.is_active == True)
    return db.exec(query).first()


def mark_qrcode_used(db: Session, qrcode: Qrcode, user_id: str) -> Optional[Qrcode]:
    qrcode.is_used = True
    qrcode.user_id = user_id
    db.commit()
    db.refresh(qrcode)
    return qrcode
