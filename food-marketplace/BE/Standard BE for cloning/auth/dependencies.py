from typing import Optional

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select
from starlette.exceptions import HTTPException

from apps.auth.models.revoked_token import RevokedToken
from apps.auth.routers import get_current_user
from apps.auth.services import decode_access_token
from apps.core.database import get_session
from apps.users.models import User

security = HTTPBearer()


class OptionalHTTPBearer(HTTPBearer):
    async def __call__(self, request: Request):
        auth = request.headers.get("Authorization")
        if not auth:
            return None
        return await super().__call__(request)


security_optional = OptionalHTTPBearer(auto_error=False)


def get_current_user_or_none(
    db: Session = Depends(get_session),
    token: Optional[HTTPAuthorizationCredentials] = Depends(security_optional),
) -> Optional[User]:
    """
    Optional authentication:
    - If Authorization header exists → validate and return user (same logic as get_authenticated_user)
    - If no header → return None
    """
    # No Authorization header → not logged in
    if token is None:
        return None

    # Token exists → decode and validate
    try:
        token_str = token.credentials
        user_data = decode_access_token(token_str)

        # Check blacklist by jti if present
        jti = user_data.get("jti")
        user_id = user_data.get("sub")

        if jti:
            revoked = db.exec(
                select(RevokedToken).where(RevokedToken.jti == jti)
            ).first()
            if revoked:
                # Token revoked → treat as unauthenticated
                return None

        # Get user from database
        user = db.exec(
            select(User).where(User.id == user_id, User.is_active == True)
        ).first()

        if not user:
            # Invalid token or inactive user → treat as unauthenticated
            return None

    except (HTTPException, Exception):
        # If token invalid → treat as unauthenticated, not error
        return None

    # Assign shop for staff_shop users
    if (
        user.permissions == "staff_shop"
        and user.code_shop
        and (not hasattr(user, "shop") or user.shop is None)
    ):
        from apps.shops.crud import get_shop_by_code

        shop = get_shop_by_code(db, user.code_shop)
        if shop:
            user.shop = shop

    return user


def get_authenticated_user(
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
    token: str = Depends(security),
) -> User:
    """
    Common dependency that provides both database session and authenticated user.
    Ensures the user object is attached to the database session to enable relationship access.

    Returns tuple of (db_session, user)

    Usage:
        @router.post("/create-something")
        def create_something(
            data: SomeSchema,
            deps: tuple[Session, User] = Depends(get_authenticated_user)
        ):
            db, user = deps
            # Can now safely access user.favorites, user.shop, etc.

    Alternative usage:
        @router.post("/create-something")
        def create_something(
            data: SomeSchema,
            db: Session = Depends(get_session),
            user: User = Depends(get_authenticated_user),
        ):
            # Use db and user...
    """
    # Ensure the user is attached to the current session to enable relationship access
    # This prevents DetachedInstanceError when accessing user.favorites, user.shop, etc.
    if user not in db:
        # Get fresh user instance attached to current session
        attached_user = db.get(User, user.id)
        if not attached_user:
            raise HTTPException(status_code=401, detail="User not found")
        user = attached_user

    # Assign shop to staff users based on their code_shop (same logic as middleware)
    if (
        user.permissions == "staff_shop"
        and user.code_shop
        and (not hasattr(user, "shop") or user.shop is None)
    ):
        from apps.shops.crud import get_shop_by_code

        shop = get_shop_by_code(db, user.code_shop)
        if shop:
            user.shop = shop

    return user
