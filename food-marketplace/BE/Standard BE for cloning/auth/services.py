import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import HTTPException
from passlib.context import CryptContext

from apps.auth.constants import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY
from apps.users.crud import get_user_by_email, get_user_by_username
from apps.users.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def authenticate_user(
    db, username: str, password: str, shop_code: Optional[str] = None
) -> Optional[User]:
    user = get_user_by_username(db, username) or get_user_by_email(db, username)
    if not user or not verify_password(password, user.password):
        return None

    # If shop_code is provided, validate it against the user's shop
    if shop_code:
        if user.code_shop != shop_code:
            return None

    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    # Ensure token has jti and token_type present in payload
    if "jti" not in to_encode:
        to_encode["jti"] = str(uuid.uuid4())
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def generate_user_tokens_service(user: User) -> dict:

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # TODO: change expired time refresh token
    refresh_token_expires = timedelta(days=7)

    access_token = create_access_token(
        data={"sub": user.id, "token_type": "access"},
        expires_delta=access_token_expires,
    )
    refresh_token = create_access_token(
        data={"sub": user.id, "token_type": "refresh"},
        expires_delta=refresh_token_expires,
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }
