from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlmodel import Session
from pydantic import BaseModel

from apps.core.database import get_session
from apps.core.schemas import SuccessResponse
from apps.auth.permissions import AdminUser, AuthenticatedUser
from apps.users.crud import get_user_by_id, get_user_by_email, get_all_users, create_user, update_user
from apps.users.schemas import UserResponse, UserUpdate

router = APIRouter(prefix="", tags=["Пользователи"])


class AdminCreateUserRequest(BaseModel):
    email: str
    password: str
    name: Optional[str] = None
    role: str  # owner_shop | owner_locker

    class Config:
        json_schema_extra = {
            "example": {"email": "shop@example.com", "password": "Aa@12345678", "name": "Shop Owner", "role": "owner_shop"}
        }


@router.get("/me", response_model=SuccessResponse[UserResponse])
def get_me(current_user: AuthenticatedUser):
    return SuccessResponse(data=current_user)


@router.put("/me", response_model=SuccessResponse[UserResponse])
def update_me(body: UserUpdate, current_user: AuthenticatedUser, db: Session = Depends(get_session)):
    user = update_user(db, current_user, body.model_dump(exclude_none=True))
    return SuccessResponse(data=user)


@router.post("/me/avatar", response_model=SuccessResponse[UserResponse])
async def upload_avatar(
    current_user: AuthenticatedUser,
    db: Session = Depends(get_session),
    file: UploadFile = File(...),
):
    from apps.integrations.file_storage import file_storage
    path = await file_storage.upload(file, subfolder="avatars")
    user = update_user(db, current_user, {"icon": path})
    return SuccessResponse(data=user, message="Аватар обновлён")


@router.get("", response_model=SuccessResponse)
def list_users(current_user: AdminUser, db: Session = Depends(get_session)):
    users = get_all_users(db)
    return SuccessResponse(data=users)


@router.put("/{user_id}/role", response_model=SuccessResponse)
def change_role(user_id: str, role: str, current_user: AdminUser, db: Session = Depends(get_session)):
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    update_user(db, user, {"role": role, "permissions": role})
    return SuccessResponse(message="Роль изменена")


@router.post("/register-by-admin", response_model=SuccessResponse[UserResponse], status_code=201)
def admin_create_user(body: AdminCreateUserRequest, current_user: AdminUser, db: Session = Depends(get_session)):
    """Admin-only: create owner_shop or owner_locker accounts."""
    allowed_roles = ("owner_shop", "owner_locker")
    if body.role not in allowed_roles:
        raise HTTPException(status_code=400, detail=f"Роль должна быть одной из: {', '.join(allowed_roles)}")
    if get_user_by_email(db, body.email):
        raise HTTPException(status_code=409, detail="Пользователь с таким email уже существует")
    from apps.auth.services import hash_password
    user = create_user(db, {
        "email": body.email,
        "password": hash_password(body.password),
        "name": body.name,
        "role": body.role,
        "permissions": body.role,
        "is_verified_email": True,
        "is_active": True,
    })
    return SuccessResponse(data=UserResponse.model_validate(user), message="Аккаунт создан")


@router.get("/by-role/{role}", response_model=SuccessResponse)
def list_users_by_role(role: str, current_user: AdminUser, db: Session = Depends(get_session)):
    """Admin-only: list users filtered by role."""
    from sqlmodel import select
    from apps.users.models import User
    users = db.exec(select(User).where(User.role == role).order_by(User.created_at.desc())).all()
    return SuccessResponse(data=[UserResponse.model_validate(u) for u in users])
