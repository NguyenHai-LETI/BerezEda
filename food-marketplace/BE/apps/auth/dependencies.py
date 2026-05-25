from typing import Optional

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from apps.users.models import User

# These make Swagger UI show the lock icon and "Authorize" button
_bearer_required = HTTPBearer()
_bearer_optional = HTTPBearer(auto_error=False)


def get_authenticated_user(
    request: Request,
    _credentials: HTTPAuthorizationCredentials = Depends(_bearer_required),
) -> User:
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def get_current_user_or_none(
    request: Request,
    _credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_optional),
) -> Optional[User]:
    """Return the authenticated user if present, otherwise None (no error)."""
    return getattr(request.state, "user", None)


def get_admin_user(user: User = Depends(get_authenticated_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def get_customer_user(user: User = Depends(get_authenticated_user)) -> User:
    if user.role != "customer":
        raise HTTPException(status_code=403, detail="Customer access required")
    return user


def get_shop_owner_or_admin_user(user: User = Depends(get_authenticated_user)) -> User:
    if user.role not in ("owner_shop", "admin"):
        raise HTTPException(
            status_code=403, detail="Shop owner or admin access required"
        )
    return user


def get_locker_owner_or_admin_user(user: User = Depends(get_authenticated_user)) -> User:
    if user.role not in ("owner_locker", "admin"):
        raise HTTPException(
            status_code=403, detail="Locker owner or admin access required"
        )
    return user


def get_shop_locker_owner_or_admin_user(user: User = Depends(get_authenticated_user)) -> User:
    if user.role not in ("owner_shop", "owner_locker", "admin"):
        raise HTTPException(
            status_code=403, detail="Shop owner, locker owner or admin access required"
        )
    return user
