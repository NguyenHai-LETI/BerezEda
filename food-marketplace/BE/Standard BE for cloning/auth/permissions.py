from typing import Annotated, List, Optional, Union

from fastapi import Depends, HTTPException
from sqlmodel import Session

from apps.auth.dependencies import get_authenticated_user, get_current_user_or_none
from apps.lockers import LockerLocation
from apps.users.models.users import User


# Clean dependency injection - no tuple unpacking needed
def get_admin_user(user: User = Depends(get_authenticated_user)) -> User:
    """Get authenticated admin user."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def get_customer_user(user: User = Depends(get_authenticated_user)) -> User:
    """Get authenticated customer user."""
    if user.role != "customer":
        raise HTTPException(status_code=403, detail="Customer access required")
    return user


def get_shop_owner_or_admin_user(user: User = Depends(get_authenticated_user)) -> User:
    """Get authenticated shop owner or admin user."""
    if user.role not in ["owner_shop", "admin"]:
        raise HTTPException(
            status_code=403, detail="Shop owner or admin access required"
        )
    return user


def get_locker_owner_or_admin_user(
    user: User = Depends(get_authenticated_user),
) -> User:
    if user.role not in ["owner_locker", "admin"]:
        raise HTTPException(
            status_code=403, detail="Locker owner or admin access required"
        )
    return user


def get_shop_locker_owner_or_admin_user(
    user: User = Depends(get_authenticated_user),
) -> User:
    """Get authenticated shop owner, locker owner or admin user."""
    if user.role not in ["owner_shop", "owner_locker", "admin"]:
        raise HTTPException(
            status_code=403,
            detail="Shop owner or locker owner or admin access required",
        )
    return user


def get_shop_owner(user: User = Depends(get_authenticated_user)) -> User:
    """Get authenticated shop owner."""
    if user.role not in ["owner_shop"] and user.permissions not in ["owner_shop"]:
        raise HTTPException(
            status_code=403, detail="Shop owner or admin access required"
        )
    return user


AdminUser = Annotated[User, Depends(get_admin_user)]
CustomerUser = Annotated[User, Depends(get_customer_user)]
ShopOwnerOrAdminUser = Annotated[User, Depends(get_shop_owner_or_admin_user)]
ShopLockerOwnerOrAdminUser = Annotated[
    User, Depends(get_shop_locker_owner_or_admin_user)
]
LockerOwnerOrAdminUser = Annotated[User, Depends(get_locker_owner_or_admin_user)]
AuthenticatedUser = Annotated[User, Depends(get_authenticated_user)]
AuthenticatedUserOrNone = Annotated[Optional[User], Depends(get_current_user_or_none)]
ShopOwner = Annotated[User, Depends(get_shop_owner)]


def require_roles(
    allowed_roles: Union[str, List[str]], error_message: Optional[str] = None
):
    """
    Dependency factory to require specific roles.

    Args:
        allowed_roles: Single role string or list of allowed roles
        error_message: Custom error message (optional)

    Returns:
        FastAPI dependency function that returns (db, user) tuple

    Usage:
        @router.get("/admin-only")
        def admin_endpoint(deps = Depends(require_roles("admin"))):
            db, user = deps

        @router.get("/shop-management")
        def shop_endpoint(deps = Depends(require_roles(["admin", "owner_shop"]))):
            db, user = deps
    """
    if isinstance(allowed_roles, str):
        allowed_roles = [allowed_roles]

    if not error_message:
        roles_str = ", ".join(allowed_roles)
        error_message = f"Access denied. Required roles: {roles_str}"

    def check_user_role(
        deps: tuple[Session, User] = Depends(get_authenticated_user),
    ) -> tuple[Session, User]:
        db, user = deps

        if user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail=error_message)

        return db, user

    return check_user_role


def can_manage_shop_products(user, shop_id: str, db: Session) -> bool:
    """
    Check if user can manage products for a specific shop.
    Returns True if user is:
    - Admin
    - Owner of the shop
    - Staff of the shop
    """
    # Admin can manage all shops
    if user.role == "admin" or user.permissions == "admin":
        return True

    # Check if user is shop owner or staff
    if user.role in ["shop", "owner_shop", "staff_shop"]:
        # For shop owners/staff, check if they belong to this shop
        if hasattr(user, "code_shop") and user.code_shop:
            # Get shop by code_shop field
            from apps.shops.crud import get_shop_by_code

            shop = get_shop_by_code(db, user.code_shop)
            if shop and shop.id == shop_id:
                return True

        # Alternative: check direct shop relationship using helper method
        associated_shop = user.get_associated_shop()
        if associated_shop and associated_shop.id == shop_id:
            return True

    return False


def can_manage_locker(user: User, location: LockerLocation) -> bool:
    if user.role == "owner_locker" and location.owner_id == user.id:
        return True
    return False
