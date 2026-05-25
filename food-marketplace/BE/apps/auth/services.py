from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import HTTPException
from passlib.context import CryptContext

from apps.auth.constants import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY
from apps.users.crud import get_user_by_email, get_user_by_username
from apps.users.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def authenticate_user(
    db, username: str, password: str, shop_code: Optional[str] = None
) -> Optional[User]:
    user = get_user_by_username(db, username) or get_user_by_email(db, username)
    if not user or not verify_password(password, user.password):
        return None
    if shop_code and getattr(user, "code_shop", None) != shop_code:
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    import uuid
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    if "jti" not in to_encode:
        to_encode["jti"] = str(uuid.uuid4())
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def generate_user_tokens_service(user: User) -> dict:
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=7)
    access_token = create_access_token(
        data={"sub": user.id, "token_type": "access"},
        expires_delta=access_token_expires,
    )
    refresh_token = create_access_token(
        data={"sub": user.id, "token_type": "refresh"},
        expires_delta=refresh_token_expires,
    )
    return {"access_token": access_token, "refresh_token": refresh_token}


def hash_password(plain: str) -> str:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.hash(plain)


def create_tokens(user) -> dict:
    return generate_user_tokens_service(user)


def refresh_access_token(db, refresh_token: str) -> dict:
    from fastapi import HTTPException
    try:
        payload = decode_access_token(refresh_token)
        if payload.get("token_type") != "refresh":
            raise HTTPException(status_code=401, detail="Неверный тип токена")
        user_id = payload.get("sub")
        from apps.users.crud import get_user_by_id
        user = get_user_by_id(db, user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        return create_tokens(user)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Неверный refresh token")


def get_current_user(db, token: str):
    from apps.users.crud import get_user_by_id
    from fastapi import HTTPException
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    user = get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    return user
