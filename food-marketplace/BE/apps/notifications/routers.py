from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from apps.core.database import get_session
from apps.core.schemas import SuccessResponse, ListResponse
from apps.auth.permissions import AuthenticatedUser
from apps.notifications.models import Notification

router = APIRouter(prefix="/notifications", tags=["Уведомления"])


@router.get("", response_model=ListResponse)
def list_notifications(current_user: AuthenticatedUser, db: Session = Depends(get_session)):
    notifs = db.exec(
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
    ).all()
    return ListResponse(data=notifs, total=len(notifs))


@router.put("/read-all", response_model=SuccessResponse)
def mark_all_read(current_user: AuthenticatedUser, db: Session = Depends(get_session)):
    notifs = db.exec(
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .where(Notification.is_read == False)
    ).all()
    for n in notifs:
        n.is_read = True
        db.add(n)
    db.commit()
    return SuccessResponse(message="Все уведомления отмечены как прочитанные")


@router.put("/{notif_id}/read", response_model=SuccessResponse)
def mark_read(notif_id: str, current_user: AuthenticatedUser, db: Session = Depends(get_session)):
    notif = db.get(Notification, notif_id)
    if notif and notif.user_id == current_user.id:
        notif.is_read = True
        db.add(notif)
        db.commit()
    return SuccessResponse(message="Отмечено как прочитанное")
