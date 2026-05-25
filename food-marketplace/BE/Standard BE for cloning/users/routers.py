from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from apps.auth.permissions import (
    AdminUser,
    AuthenticatedUser,
    LockerOwnerOrAdminUser,
    ShopOwner,
    ShopOwnerOrAdminUser,
)
from apps.auth.services import generate_user_tokens_service
from apps.core.database import get_session
from apps.core.schemas import ListResponse, SuccessResponse

from . import schemas, services
from .constants import PROCESS_COMPLETED_MESSAGE

security = HTTPBearer()
router = APIRouter(tags=["Users"])


@router.get("/", response_model=ListResponse[schemas.UserRead])
def list_users(
    user: AdminUser,
    db: Session = Depends(get_session),
    limit: int = 20,
    offset: int = 0,
    permissions: Optional[List[str]] = Query(
        None, description="Filter users by multiple permissions"
    ),
    name: Optional[str] = Query(None),
):
    """
    List users with optional filtering by multiple permissions and name.
    Returns shop information if user owns a shop.

    Args:
        permissions: List of permissions to filter by (e.g., ['owner_shop', 'owner_locker', 'customer'])
        name: Filter users by name:
            - For 'customer' permission: searches in 'name' field
            - For 'owner_shop' or 'owner_locker' permissions: searches in 'username' field
            - When no permissions specified: searches in 'username' field (default)
    """
    users, total = services.list_users_service(
        db, limit=limit, offset=offset, permissions=permissions, name=name
    )
    # Build user response with shop information when available
    user_data = []
    for user_obj in users:
        associated_shop = user_obj.get_associated_shop()
        if associated_shop:
            user_data.append(schemas.UserRead.build(user_obj, associated_shop))
        else:
            user_data.append(schemas.UserRead.build(user_obj, None))

    return ListResponse(limit=limit, offset=offset, total=total, data=user_data)


@router.get("/notification", response_model=ListResponse[schemas.UserRead])
def list_users_for_notification(
    user: LockerOwnerOrAdminUser,
    db: Session = Depends(get_session),
    limit: int = 20,
    offset: int = 0,
    permission: Optional[List[str]] = Query(
        None, description="Filter users by multiple permissions"
    ),
    email: Optional[str] = Query(
        None, description="Email value to filter (partial match, case-insensitive)"
    ),
    is_not_email: Optional[str] = Query(None, description="Email value to exclude"),
    phone_number: Optional[str] = Query(None, description="Phone value to filter"),
    is_not_phone_number: Optional[str] = Query(
        None, description="Phone value to exclude"
    ),
    e_birthday: Optional[str] = Query(
        None, description="Birthday value in YYYY-MM-DD format"
    ),
    is_not_birthday: Optional[str] = Query(
        None, description="Birthday value in YYYY-MM-DD format to exclude"
    ),
    lte_birthday: Optional[str] = Query(
        None,
        description="Filter birthday < lte_birthday (YYYY-MM-DD format). Can be used alone or with gte_birthday for range.",
    ),
    gte_birthday: Optional[str] = Query(
        None,
        description="Filter birthday > gte_birthday (YYYY-MM-DD format). Can be used alone or with lte_birthday for range.",
    ),
    town: Optional[str] = Query(None, description="Town name to search in address"),
    gender: Optional[str] = Query(
        None, description="Gender filter: male, female, or other"
    ),
):
    """
    List users with advanced filtering for notification purposes.

    Filter conditions (all combined with AND):
    1. Email:
       - If email is provided: partial match (case-insensitive search with ilike)
       - If is_not_email is provided: EXCLUDE match (email != is_not_email)
       - If neither is provided: no filter (search all)
    2. Phone:
       - If phone_number is provided: partial match (case-insensitive search with ilike)
       - If is_not_phone_number is provided: EXCLUDE match (phone != is_not_phone_number)
       - If neither is provided: no filter (search all)
    3. Birthday:
       - If e_birthday is provided: EXACT match (birthday = e_birthday)
       - If is_not_birthday is provided: EXCLUDE match (birthday != is_not_birthday)
       - If lte_birthday and gte_birthday are both provided: RANGE match (start_date <= birthday <= end_date)
       - If only lte_birthday is provided: birthday < lte_birthday
       - If only gte_birthday is provided: birthday > gte_birthday
       - If none are provided: no filter (search all)
    4. Town: Search town in User.address (case-insensitive partial match)
    5. Gender: male, female, or other (maps to Japanese values: "男性", "女性", "その他" in database)
    """
    users, total = services.list_users_for_notification_service(
        db=db,
        limit=limit,
        offset=offset,
        permission=permission,
        email=email,
        is_not_email=is_not_email,
        phone_number=phone_number,
        is_not_phone_number=is_not_phone_number,
        e_birthday=e_birthday,
        is_not_birthday=is_not_birthday,
        lte_birthday=lte_birthday,
        gte_birthday=gte_birthday,
        town=town,
        gender=gender,
    )

    # Build user response with shop information when available
    user_data = []
    for user_obj in users:
        associated_shop = user_obj.get_associated_shop()
        if associated_shop:
            user_data.append(schemas.UserRead.build(user_obj, associated_shop))
        else:
            user_data.append(schemas.UserRead.build(user_obj, None))

    return ListResponse(limit=limit, offset=offset, total=total, data=user_data)


@router.get("/user/{user_id}", response_model=SuccessResponse[schemas.UserRead])
def get_user_by_id(
    user_id: str,
    user: AdminUser,
    db: Session = Depends(get_session),
):
    user_obj = services.get_user_by_id_service(db, user_id)
    associated_shop = user_obj.get_associated_shop()
    if associated_shop:
        user_obj = schemas.UserRead.build(user_obj, associated_shop)
    elif (
        hasattr(user_obj, "owned_locker_locations") and user_obj.owned_locker_locations
    ):
        user_obj = schemas.UserRead.build_locker(
            user_obj, user_obj.owned_locker_locations
        )
    else:
        user_obj = schemas.UserRead.build(user_obj, None)

    return SuccessResponse(data=user_obj)


@router.post("/", response_model=SuccessResponse)
def create_user(user: schemas.CustomerCreate, db: Session = Depends(get_session)):
    """
    Create a new customer user with auto-login (public registration).
    This endpoint is public and only allows customer role.
    Returns user data along with access and refresh tokens.
    """
    user_data = user.model_dump()
    user_create = schemas.UserCreate(**user_data)

    user_obj = services.create_user_service(user_create, db)
    token_data = generate_user_tokens_service(user_obj)

    user_read = schemas.UserRead.build(user_obj, user_obj.shop)
    return SuccessResponse(
        data={
            "refresh": token_data["refresh_token"],
            "access": token_data["access_token"],
            "user": user_read,
        }
    )


@router.post("/admin", response_model=SuccessResponse[schemas.UserRead])
def create_user_by_admin(
    user: schemas.UserCreate,
    admin_user: AdminUser,
    db: Session = Depends(get_session),
):
    """
    Create a new user by admin.
    - For shop users: Password will be auto-generated and sent via email
    - Only admin can create shop and locker users.
    - Requires admin authentication.
    """
    user_obj = services.create_user_service(user, db, created_by_admin=True)
    return SuccessResponse(
        data=schemas.UserRead.build(user_obj, user_obj.get_associated_shop())
    )


@router.get("/me", response_model=SuccessResponse[schemas.UserRead])
def get_my_profile(
    user: AuthenticatedUser,
    db: Session = Depends(get_session),
):
    """
    Get current user's profile.
    Returns the authenticated user's information including shop details if applicable.
    """
    associated_shop = user.get_associated_shop()
    if associated_shop:
        return SuccessResponse(data=schemas.UserRead.build(user, associated_shop))

    return SuccessResponse(data=schemas.UserRead.build(user, None))


@router.put("/me", response_model=SuccessResponse[schemas.UserRead])
def update_my_profile(
    update: schemas.UserUpdate,
    user: AuthenticatedUser,
    db: Session = Depends(get_session),
):
    """
    Update current user's profile.
    Users can only update their own information.
    """
    user_obj = services.update_user_service(user, db, update)
    associated_shop = user_obj.get_associated_shop()
    if associated_shop:
        return SuccessResponse(data=schemas.UserRead.build(user_obj, associated_shop))

    return SuccessResponse(data=schemas.UserRead.build(user_obj, None))


@router.delete("/admin/{user_id}", response_model=SuccessResponse)
def delete_user_by_admin(
    user_id: str,
    user: ShopOwnerOrAdminUser,
    db: Session = Depends(get_session),
):
    """
    Delete any user account (admin only).
    Only admin can delete other users.
    """
    services.delete_user_service(user_id, db, user)
    return SuccessResponse(data=None)


@router.delete("/me", response_model=SuccessResponse)
def delete_my_profile(user: AuthenticatedUser, db: Session = Depends(get_session)):
    """
    Delete current user's account.
    Users can only delete their own account.
    """
    services.delete_user_service(user.id, db, user)
    return SuccessResponse(data=None)


@router.get("/staff", response_model=ListResponse[schemas.UserRead])
def get_shop_staff(
    user: ShopOwnerOrAdminUser,
    db: Session = Depends(get_session),
    limit: int = 20,
    offset: int = 0,
):
    """
    Get list of staff for the authenticated user's shop.

    Access restricted to:
    - Admin users (can see all staff)
    - Shop owners (can see their shop's staff)

    Returns:
        List of staff users working at the owner's shop
    """
    staff_list, total = services.get_shop_staff_service(db, user, limit, offset)

    return ListResponse(
        limit=limit,
        offset=offset,
        total=total,
        data=[schemas.UserRead.build(staff, None) for staff in staff_list],
    )


@router.get("/staff/{staff_id}", response_model=SuccessResponse[schemas.UserRead])
def get_staff_by_id(
    staff_id: str,
    user: ShopOwner,
    db: Session = Depends(get_session),
):
    staff_obj = services.get_staff_by_id_service(staff_id, db, user)
    return SuccessResponse(data=schemas.UserRead.build(staff_obj, None))


@router.put("/staff/{staff_id}", response_model=SuccessResponse[schemas.UserRead])
def update_staff_by_id(
    staff_id: str,
    update: schemas.UserUpdate,
    user: ShopOwner,
    db: Session = Depends(get_session),
):
    staff_obj = services.update_staff_by_id_service(staff_id, update, db, user)
    return SuccessResponse(data=schemas.UserRead.build(staff_obj, None))


@router.post("/staff", response_model=SuccessResponse[schemas.UserRead])
def create_shop_staff(
    shop_owner: ShopOwner,
    staff: schemas.StaffCreate,
    db: Session = Depends(get_session),
):
    staff_data = staff.model_dump()
    staff_create = schemas.StaffCreate(**staff_data)
    staff_obj = services.create_staff_service(staff_create, db, shop_owner)
    return SuccessResponse(data=schemas.UserRead.build(staff_obj, None))


@router.post("/forgot-password", response_model=SuccessResponse)
def forgot_password(
    request: schemas.ForgotPasswordRequest,
    db: Session = Depends(get_session),
):

    result = services.forgot_password_service(request.email, db)
    return SuccessResponse(message=result, data=None)


@router.post("/verify-code", response_model=SuccessResponse)
def verify_reset_code(
    request: schemas.VerifyResetCodeRequest,
    db: Session = Depends(get_session),
):
    msg, data = services.verify_reset_code_service(
        request.email, request.code, request.new_password, db
    )
    return SuccessResponse(message=msg, data=data)


@router.post("/reset-password", response_model=SuccessResponse)
def reset_password(
    request: schemas.ResetPasswordRequest,
    db: Session = Depends(get_session),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    session_token = credentials.credentials
    services.reset_password_service(
        request.password, request.confirm_password, session_token, db
    )
    return SuccessResponse(message=PROCESS_COMPLETED_MESSAGE, data=None)


@router.put("/admin/{user_id}", response_model=SuccessResponse[schemas.UserRead])
def update_user_by_admin(
    user_id: str,
    update: schemas.AdminUserUpdate,
    admin_user: AdminUser,
    db: Session = Depends(get_session),
):
    updated_user = services.update_user_by_admin_service(
        user_id, update, db, admin_user
    )

    shop_obj = None
    associated_shop = updated_user.get_associated_shop()
    if associated_shop:
        shop_obj = associated_shop
    return SuccessResponse(data=schemas.UserRead.build(updated_user, shop_obj))
