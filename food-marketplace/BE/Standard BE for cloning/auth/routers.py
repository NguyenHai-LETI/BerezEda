from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from apps.auth import crud, services
from apps.auth.constants import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY
from apps.auth.exceptions import invalid_shop_credentials, unauthorized
from apps.auth.schemas import (
    LogoutRequest,
    RefreshToken,
    RefreshTokenRequest,
    UserLogin,
)
from apps.auth.services import (
    authenticate_user,
    create_access_token,
    decode_access_token,
)
from apps.core.database import get_session
from apps.core.schemas import SuccessResponse
from apps.devices.services import unlink_device_from_user_service
from apps.shops.crud import get_shop_by_code
from apps.users.models import User
from apps.users.schemas import UserRead

router = APIRouter(tags=["Auth"])
http_bearer = HTTPBearer()


def _update_myna_portal_status(user: User, db: Session) -> None:
    """
    Check and update user's my_portal status based on active welfare supports.
    """
    # Import here to avoid circular import
    from apps.mynaportal.services import has_active_welfare_support

    # Check if user has any active welfare support
    is_supported = has_active_welfare_support(db, user.id)

    new_status = "linked" if is_supported else "not linked"

    if user.my_portal != new_status:
        user.my_portal = new_status
        db.add(user)
        db.commit()


@router.post("/token", response_model=SuccessResponse[dict])
def login_for_access_token_json(body: UserLogin, db: Session = Depends(get_session)):

    user = authenticate_user(db, body.username, body.password, body.shop_code)
    if not user:
        if body.shop_code:
            raise invalid_shop_credentials()
        else:
            raise unauthorized()

    # Check and update my_portal status based on active welfare supports
    _update_myna_portal_status(user, db)

    shop = user.get_associated_shop()
    if user.role == "owner_shop" and not shop and user.code_shop:
        shop = get_shop_by_code(db, user.code_shop)

    token_data = services.generate_user_tokens_service(user)
    user_data = UserRead.build(user, shop).model_dump()
    return SuccessResponse(
        data={
            "refresh": token_data["refresh_token"],
            "access": token_data["access_token"],
            "user": user_data,
        }
    )


@router.post("/refresh-token", response_model=SuccessResponse[RefreshToken])
def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_session),
):
    try:
        payload = jwt.decode(request.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        # Check blacklist for refresh token by jti
        jti = payload.get("jti")
        if not jti:
            raise HTTPException(status_code=401, detail="Invalid token")
        revoked = crud.get_revoked_token_by_jti(db, jti)
        if revoked:
            raise HTTPException(status_code=401, detail="Token revoked")
        user_id = payload.get("sub")
        if not user_id or payload.get("token_type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token")
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        new_access_token = create_access_token(
            {"sub": user_id, "token_type": "access"},
            expires_delta=access_token_expires,
        )
        refresh_token_response = RefreshToken(
            access_token=new_access_token, token_type="bearer"
        )
        return SuccessResponse(data=refresh_token_response)

    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_current_user(request: Request) -> User:
    """Dependency to get the current authenticated user from request state."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="User not found in request state")
    return user


@router.post("/logout", response_model=SuccessResponse[None])
def logout(
    body: LogoutRequest,
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer),
    db: Session = Depends(get_session),
):
    # Get user ID from the access token
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
    except HTTPException:
        raise unauthorized()

    if not user_id:
        raise unauthorized()

    # Unlink device from user if provided (set user_id = null)
    if body.device_token:
        unlink_device_from_user_service(body.device_token, user_id, db)

    # Revoke tokens
    tokens_to_revoke: list[str] = [credentials.credentials]
    if body.refresh_token:
        tokens_to_revoke.append(body.refresh_token)

    for token in tokens_to_revoke:
        try:
            payload = decode_access_token(token)
        except HTTPException:
            continue
        jti = payload.get("jti")
        sub = payload.get("sub")
        token_type = payload.get("token_type")
        exp = payload.get("exp")
        if not jti or not sub or not token_type or not exp:
            continue
        exists = crud.get_revoked_token_by_jti(db, jti)
        if exists:
            continue
        expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
        crud.create_revoked_token(
            db,
            jti=jti,
            user_id=sub,
            token_type=token_type,
            expires_at=expires_at,
        )
    return SuccessResponse(data=None)
