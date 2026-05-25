from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from pydantic import BaseModel
from typing import Optional

from apps.core.database import get_session
from apps.core.schemas import SuccessResponse
from apps.auth.services import authenticate_user, create_tokens, refresh_access_token
from apps.auth.crud import revoke_token
from apps.auth.permissions import AuthenticatedUser
from apps.users.crud import get_user_by_email, create_user
from apps.users.schemas import UserResponse

router = APIRouter(tags=["Авторизация"])


class LoginRequest(BaseModel):
    email: str
    password: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "customer1@example.com",
                "password": "Aa@12345678",
            }
        }
    }


class RefreshRequest(BaseModel):
    refresh_token: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


@router.post("/token", response_model=SuccessResponse[TokenResponse])
def login(body: LoginRequest, db: Session = Depends(get_session)):
    user = authenticate_user(db, body.email, body.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный email или пароль")
    tokens = create_tokens(user)
    return SuccessResponse(data=TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        user=UserResponse.model_validate(user),
    ))


@router.post("/register", response_model=SuccessResponse[TokenResponse], status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_session)):
    if get_user_by_email(db, body.email):
        raise HTTPException(status_code=409, detail="Пользователь с таким email уже существует")
    from apps.auth.services import hash_password
    user = create_user(db, {
        "email": body.email,
        "password": hash_password(body.password),
        "name": body.name,
        "role": "customer",
        "permissions": "customer",
        "is_verified_email": True,
        "is_active": True,
    })
    tokens = create_tokens(user)
    return SuccessResponse(
        data=TokenResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            user=UserResponse.model_validate(user),
        ),
        message="Аккаунт создан",
    )


@router.post("/refresh", response_model=SuccessResponse)
def refresh(body: RefreshRequest, db: Session = Depends(get_session)):
    result = refresh_access_token(db, body.refresh_token)
    return SuccessResponse(data=result)


@router.post("/logout", response_model=SuccessResponse)
def logout(current_user: AuthenticatedUser, db: Session = Depends(get_session)):
    # Revoke handled by middleware already
    return SuccessResponse(message="Выход выполнен")
