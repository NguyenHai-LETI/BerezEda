import json
import random
import secrets
import time
from datetime import timedelta
from typing import List, Optional, Union

import jwt
from sqlmodel import Session

from apps.auth.constants import ALGORITHM, SECRET_KEY
from apps.auth.services import get_password_hash
from apps.core.config import RESET_CODE_EXPIRE_MINUTES, SESSION_TOKEN_EXPIRE_MINUTES
from apps.core.schemas import DEFAULT_LIMIT, DEFAULT_OFFSET
from apps.core.utils import get_current_time
from apps.integrations.mail.email_service import (
    generate_random_password,
    send_staff_creation_email,
)
from apps.integrations.redis.redis_client import get_redis_client
from apps.shops.crud import get_shop_by_code, update_shop
from apps.shops.models import Shop
from apps.shops.schemas import ShopCreate
from apps.shops.services import create_shop_service
from apps.users import crud, schemas
from apps.users.constants import (
    MESSAGE_CONFIRM_CODE,
    PROCESS_COMPLETED_MESSAGE,
    SUCCESS_VERIFY_CODE_MESSAGE,
)
from apps.users.crud import get_user_by_email
from apps.users.exceptions import (
    code_expired,
    email_not_found,
    insufficient_permissions,
    invalid_reset_code,
    invalid_session_purpose,
    invalid_session_token,
    user_not_found,
)
from apps.users.models.users import User
from apps.users.tasks import send_reset_password_email_task
from apps.users.validators import (
    set_user_permissions,
    validate_and_parse_birthday_fields,
    validate_email_uniqueness,
    validate_forgot_password_rate_limit,
    validate_notification_user_filters,
    validate_password_match,
    validate_reset_password_rate_limit,
    validate_shop_owner_permissions,
    validate_staff_belong_to_shop,
    validate_staff_removal_permission,
    validate_user_exists,
    validate_user_role,
    validate_user_uniqueness,
)


def generate_reset_code() -> str:
    return f"{random.randint(100000, 999999)}"


def create_session_token(
    user_id: str,
    purpose: str = "password_reset",
    expires_minutes: int = SESSION_TOKEN_EXPIRE_MINUTES,
) -> str:
    expire = get_current_time() + timedelta(minutes=expires_minutes)
    token_data = {
        "sub": user_id,
        "purpose": purpose,
        "exp": expire,
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)


def decode_session_token(token: str) -> dict:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return {
        "valid": True,
        "user_id": payload.get("sub"),
        "purpose": payload.get("purpose"),
    }


def _prepare_user_data(user: Union[schemas.UserCreate, schemas.StaffCreate]) -> dict:
    user_type = user.role

    if user_type == "customer":
        user_data = user.model_dump(exclude={"shop"})
    elif user_type in ["admin", "owner_locker", "owner_shop"]:
        user_data = user.model_dump(exclude={"shop"})
        if not hasattr(user, "username") or user.username is None:
            user_data["username"] = None
    else:
        validate_user_role(user_type)

    if hasattr(user, "first_name") and hasattr(user, "last_name"):
        if user.first_name and user.last_name:
            user_data["name"] = f"{user.first_name} {user.last_name}".strip()
        elif user.first_name:
            user_data["name"] = user.first_name.strip()
        elif user.last_name:
            user_data["name"] = user.last_name.strip()

    user_data = set_user_permissions(user_data, user_type)

    if hasattr(user, "password") and getattr(user, "password", None):
        user_data["password"] = get_password_hash(user_data["password"])
    elif "password" in user_data and user_data["password"]:
        user_data["password"] = get_password_hash(user_data["password"])

    return user_data


def _create_shop_for_user(user: schemas.UserCreate, user_obj: User, db: Session):
    if user.role == "owner_shop" and user.shop:
        # Create ShopCreate schema with owner_id
        shop_create_data = user.shop.model_dump()
        shop_create_data["owner_id"] = str(user_obj.id)
        shop_create_schema = ShopCreate(**shop_create_data)

        # Use the shop creation service - pass user_obj for is_favorite check
        new_shop_schema = create_shop_service(shop_create_schema, user_obj, db)
        user_obj.code_shop = new_shop_schema.code


def create_user_service(
    user: schemas.UserCreate, db: Session, created_by_admin: bool = False
):
    original_password = None

    # For shop users created by admin, auto-generate password
    if created_by_admin and (user.role == "owner_shop" or user.role == "owner_locker"):
        original_password = generate_random_password()
        user.password = original_password

    # Validate uniqueness constraints
    validate_user_uniqueness(user, db)

    # Prepare user data
    user_data = _prepare_user_data(user)
    new_user = User(**user_data)

    user_obj = crud.create_user(db, new_user)
    _create_shop_for_user(user, user_obj, db)

    db.commit()
    db.refresh(user_obj)

    # Sync user to Firebase asynchronously
    from apps.users.tasks import sync_user_to_firebase_task

    user_data = {
        "id": str(user_obj.id),
        "email": user_obj.email,
        "role": user_obj.role,
        "permissions": user_obj.permissions,
        "is_active": user_obj.is_active,
        "code_shop": user_obj.code_shop,
        "created_at": user_obj.created_at.isoformat() if user_obj.created_at else None,
        "updated_at": user_obj.updated_at.isoformat() if user_obj.updated_at else None,
    }
    sync_user_to_firebase_task(user_data)

    # Send email for admin-created shop users and locker owner
    if (
        created_by_admin
        and (user.role == "owner_shop" or user.role == "owner_locker")
        and user.email
        and original_password
    ):
        email_sent = send_staff_creation_email(
            user_email=str(user.email),
            user_data={
                "code_shop": user_obj.code_shop,
                "name": user_obj.name,
                "role": user_obj.role,
            },
            password=original_password,
        )

    return user_obj


def get_user_service(user_id: str, db: Session):
    user = crud.get_user(db, user_id)
    validate_user_exists(user)
    return user


def update_user_service(user: User, db: Session, update: schemas.UserUpdate):
    if update.email and update.email != user.email:
        validate_email_uniqueness(str(update.email), db)

    update_data = update.model_dump(
        exclude_unset=True, exclude={"shop", "password", "email", "permissions"}
    )

    if update.first_name is not None or update.last_name is not None:
        first_name = (
            update.first_name if update.first_name is not None else user.first_name
        )
        last_name = update.last_name if update.last_name is not None else user.last_name
        if first_name and last_name:
            update_data["name"] = f"{first_name} {last_name}".strip()
        elif first_name:
            update_data["name"] = first_name.strip()
        elif last_name:
            update_data["name"] = last_name.strip()

    for field, value in update_data.items():
        setattr(user, field, value)

    if update.email:
        user.email = str(update.email)

    if update.password:
        user.password = get_password_hash(update.password)

    if update.shop and user.role == "owner_shop":
        if user.code_shop:
            shop = db.query(Shop).filter_by(code=user.code_shop).first()
            if shop:
                shop.name = update.shop.name
                shop.address = update.shop.address
                shop.phone = update.shop.phone
                shop.logo = update.shop.logo
                shop.position = update.shop.position
        else:
            _create_shop_for_user(
                schemas.UserCreate(**{**user.__dict__, "shop": update.shop}), user, db
            )

    user = crud.update_user(db, user)
    return user


def delete_user_service(user_id: str, db: Session, user: User):
    staff_user = crud.get_user(db, user_id)
    validate_staff_removal_permission(staff_user, user)
    # After validation, staff_user is guaranteed to exist
    assert staff_user is not None
    crud.delete_user(db, staff_user)

    # Delete user from Firebase asynchronously
    from apps.users.tasks import delete_user_from_firebase_task

    delete_user_from_firebase_task(user_id)

    return None


def list_users_service(
    db: Session,
    limit: int = DEFAULT_LIMIT,
    offset: int = DEFAULT_OFFSET,
    permissions: Optional[List[str]] = None,
    name: Optional[str] = None,
):
    users, total = crud.list_users(db, limit, offset, permissions, name)
    return users, total


def list_users_for_notification_service(
    db: Session,
    limit: int = DEFAULT_LIMIT,
    offset: int = DEFAULT_OFFSET,
    permission: Optional[List[str]] = None,
    email: Optional[str] = None,
    is_not_email: Optional[str] = None,
    phone_number: Optional[str] = None,
    is_not_phone_number: Optional[str] = None,
    e_birthday: Optional[str] = None,
    is_not_birthday: Optional[str] = None,
    lte_birthday: Optional[str] = None,
    gte_birthday: Optional[str] = None,
    town: Optional[str] = None,
    gender: Optional[str] = None,
):
    """
    Service function to list users with advanced filtering for notifications.
    """
    # Validate all filter parameters
    validate_notification_user_filters(
        email=email,
        is_not_email=is_not_email,
        phone_number=phone_number,
        is_not_phone_number=is_not_phone_number,
        e_birthday=e_birthday,
        is_not_birthday=is_not_birthday,
        lte_birthday=lte_birthday,
        gte_birthday=gte_birthday,
        gender=gender,
    )
    # Convert empty list or list with empty strings to None
    if permission is not None:
        # Filter out empty strings from the list
        permission = [p for p in permission if p and p.strip()]
        # If list becomes empty, set to None
        if not permission:
            permission = None

    # Map gender to database values
    gender_values = None
    if gender:
        gender_lower = gender.lower()
        # Map English to Japanese gender values
        # Common Japanese values: "男性" (male), "女性" (female), "その他" (other), "male", "female"
        gender_mapping = {
            "male": ["男性", "male", "MALE"],
            "female": ["女性", "female", "FEMALE"],
            "other": ["その他", "other", "OTHER"],
        }
        gender_values = gender_mapping[gender_lower]

    # Validate and parse birthday fields
    birthday_date, start_date, end_date = validate_and_parse_birthday_fields(
        e_birthday=e_birthday,
        is_not_birthday=is_not_birthday,
        lte_birthday=lte_birthday,
        gte_birthday=gte_birthday,
    )

    # Determine birthday filter flags
    is_exclude_birthday = bool(is_not_birthday)
    # Range mode: both lte_birthday and gte_birthday are provided
    # Single filter mode: only one of lte_birthday or gte_birthday is provided
    is_range_birthday = bool(lte_birthday and gte_birthday)
    is_lte_birthday_only = bool(lte_birthday and not gte_birthday)
    is_gte_birthday_only = bool(gte_birthday and not lte_birthday)

    users, total = crud.list_users_for_notification(
        db=db,
        limit=limit,
        offset=offset,
        permission=permission,
        email=email,
        is_not_email=is_not_email,
        phone_number=phone_number,
        is_not_phone_number=is_not_phone_number,
        is_exclude_birthday=is_exclude_birthday,
        is_range_birthday=is_range_birthday,
        is_lte_birthday_only=is_lte_birthday_only,
        is_gte_birthday_only=is_gte_birthday_only,
        birthday_date=birthday_date,
        start_date=start_date,
        end_date=end_date,
        town=town,
        gender_values=gender_values,
    )

    return users, total


def get_user_by_id_service(db: Session, user_id: str):
    user_obj = crud.get_user(db, user_id)
    if not user_obj:
        return None
    return user_obj


def get_shop_staff_service(
    db: Session, user: User, limit: int = DEFAULT_LIMIT, offset: int = DEFAULT_OFFSET
):
    """
    Get staff list for a shop owner's shop or all staff for admin.

    Args:
        db: Database session
        user: Authenticated user (must be admin or shop owner)
        limit: Maximum number of results
        offset: Number of results to skip

    Returns:
        Tuple of (staff_list, total_count)
    """
    if user.role == "admin":
        # Admin can see all staff across all shops
        staff_list, total = crud.get_all_shop_staff(db, limit, offset)
    elif user.role == "owner_shop":
        # Shop owner can only see their own shop's staff
        if not validate_shop_owner_permissions(user):
            return [], 0

        associated_shop = user.get_associated_shop()
        if not associated_shop:
            return [], 0
        staff_list, total = crud.get_staff_by_shop_code(
            db, associated_shop.code, limit, offset
        )
    else:
        # Should not reach here due to router permission check, but safety fallback
        return [], 0

    return staff_list, total


def get_staff_by_id_service(staff_id: str, db: Session, shop: User):

    staff_user = crud.get_staff_by_id(db, staff_id)
    if not staff_user:
        raise user_not_found()
    if validate_staff_belong_to_shop(staff_user, shop):
        return staff_user
    else:
        raise insufficient_permissions()


def update_staff_by_id_service(
    staff_id: str, update: schemas.UserUpdate, db: Session, user: User
):

    staff_user = crud.get_staff_by_id(db, staff_id)
    if not staff_user:
        raise user_not_found()

    if not validate_staff_belong_to_shop(staff_user, user):
        raise insufficient_permissions()

    return update_user_service(staff_user, db, update)


def create_staff_service(user: schemas.StaffCreate, db: Session, shop_owner: User):
    validate_user_uniqueness(user, db)

    password_plaint_text = user.password
    user_data = _prepare_user_data(user)
    user_data["code_shop"] = shop_owner.code_shop
    new_user = User(**user_data)

    user_obj = crud.create_user(db, new_user)

    # Establish the relationship with the shop owner's shop
    if shop_owner.owned_shop:
        user_obj.shop_id = shop_owner.owned_shop.id
        user_obj.shop = shop_owner.owned_shop

    db.commit()
    db.refresh(user_obj)

    # Sync staff user to Firebase asynchronously
    from apps.users.tasks import sync_user_to_firebase_task

    user_data = {
        "id": str(user_obj.id),
        "email": user_obj.email,
        "role": user_obj.role,
        "permissions": user_obj.permissions,
        "is_active": user_obj.is_active,
        "code_shop": user_obj.code_shop,
        "created_at": user_obj.created_at.isoformat() if user_obj.created_at else None,
        "updated_at": user_obj.updated_at.isoformat() if user_obj.updated_at else None,
    }

    sync_user_to_firebase_task(user_data)

    email_sent = send_staff_creation_email(
        user_email=str(user.email),
        user_data={
            "name": user_obj.name,
            "role": user_obj.role,
        },
        password=password_plaint_text,
    )

    return user_obj


def _parse_redis_code_data(code_data_raw) -> dict | None:
    if not code_data_raw:
        return None

    try:
        # Handle different redis client response types
        if isinstance(code_data_raw, bytes):
            code_data_str = code_data_raw.decode("utf-8")
        else:
            code_data_str = str(code_data_raw)

        return json.loads(code_data_str)
    except (json.JSONDecodeError, KeyError):
        return None


def invalidate_user_reset_codes(user_id: str, redis_client) -> None:
    if not redis_client:
        return

    # Get all keys that match the pattern for reset codes
    pattern = "reset_code:*"
    keys = redis_client.keys(pattern)

    for key in keys:
        code_data_raw = redis_client.get(key)
        code_data = _parse_redis_code_data(code_data_raw)

        if not code_data:
            continue

        if code_data.get("user_id") == user_id and not code_data.get("used", False):
            code_data["used"] = True
            redis_client.setex(
                key, RESET_CODE_EXPIRE_MINUTES * 60, json.dumps(code_data)
            )


def forgot_password_service(email: str, db: Session) -> dict:
    redis_client = get_redis_client()

    validate_forgot_password_rate_limit(email, redis_client)
    user = crud.get_user_by_email(db, email)

    if not user:
        raise email_not_found()

    reset_code = generate_reset_code()
    timestamp = int(time.time())

    if redis_client:
        # Invalidate all existing reset codes for this user
        invalidate_user_reset_codes(user.id, redis_client)

        # Create new reset code
        redis_key = f"reset_code:{reset_code}"
        code_data = {
            "user_id": user.id,
            "email": email,
            "created_at": timestamp,
            "used": False,
            "attempts": 0,
        }
        redis_client.setex(
            redis_key, RESET_CODE_EXPIRE_MINUTES * 60, json.dumps(code_data)
        )

    send_reset_password_email_task.delay(user.id, user.email, reset_code)

    return MESSAGE_CONFIRM_CODE


def verify_reset_code_service(
    email: str, code: str, new_password: Optional[str], db: Session
):
    redis_client = get_redis_client()

    redis_key = f"reset_code:{code}"
    code_data_raw = redis_client.get(redis_key) if redis_client else None

    if not code_data_raw:
        raise invalid_reset_code()

    code_data = _parse_redis_code_data(code_data_raw)
    if not code_data:
        raise invalid_reset_code()

    # Check if code is already used
    if code_data.get("used", False):
        raise invalid_reset_code()

    # Check if email matches
    if code_data.get("email") != email:
        raise invalid_reset_code()

    # Check expiration
    current_time = time.time()
    if current_time - code_data.get("created_at", 0) > RESET_CODE_EXPIRE_MINUTES * 60:
        raise code_expired()

    if new_password:
        user = get_user_by_email(db, email)
        new_password_hash = get_password_hash(new_password)
        user = crud.update_user_password(db, user.id, new_password_hash)
        return [PROCESS_COMPLETED_MESSAGE, None]
    # Code is valid - create session token
    user_id = code_data.get("user_id")
    session_token = create_session_token(user_id)

    # Mark code as used
    code_data["used"] = True
    redis_client.setex(redis_key, RESET_CODE_EXPIRE_MINUTES * 60, json.dumps(code_data))
    data_response = {
        "session_token": session_token,
        "expires_in": SESSION_TOKEN_EXPIRE_MINUTES * 60,
        "user_info": {"email": email, "user_id": user_id},
    }
    return [SUCCESS_VERIFY_CODE_MESSAGE, data_response]


def reset_password_service(
    new_password: str, confirm_password: str, session_token: str, db: Session
):
    redis_client = get_redis_client()

    validate_reset_password_rate_limit(session_token, redis_client)

    validate_password_match(new_password, confirm_password)

    token_validation = decode_session_token(session_token)
    if not token_validation["valid"]:
        raise invalid_session_token()

    if token_validation.get("purpose") != "password_reset":
        raise invalid_session_purpose()

    user_id = token_validation["user_id"]

    new_password_hash = get_password_hash(new_password)
    user = crud.update_user_password(db, user_id, new_password_hash)
    validate_user_exists(user)

    return None


def update_user_by_admin_service(
    user_id: str, update: schemas.AdminUserUpdate, db: Session, admin_user: User
):
    target_user = crud.get_user(db, user_id)
    if not target_user:
        raise user_not_found()

    if target_user.role not in ["owner_locker", "owner_shop"]:
        raise insufficient_permissions()

    update_data = update.model_dump(exclude_unset=True)

    allowed_fields = ["first_name", "last_name", "phone", "icon", "gender", "birthday"]
    for field, value in update_data.items():
        if field in allowed_fields and value is not None:
            setattr(target_user, field, value)

    if "first_name" in update_data or "last_name" in update_data:
        first_name = update_data.get("first_name", target_user.first_name)
        last_name = update_data.get("last_name", target_user.last_name)

        if first_name and last_name:
            target_user.name = f"{first_name} {last_name}".strip()
        elif first_name:
            target_user.name = first_name.strip()
        elif last_name:
            target_user.name = last_name.strip()

    # Handle shop update for owner_shop only
    if target_user.role == "owner_shop" and update_data["shop"] is not None:
        shop_update = update_data["shop"]
        shop = get_shop_by_code(db, target_user.code_shop)
        if shop:
            for field in ("position", "address", "logo", "name", "phone"):
                value = shop_update.get(field)
                if value is not None:
                    setattr(shop, field, value)
            shop.updated_at = get_current_time()
            update_shop(db, shop)

    target_user.updated_at = get_current_time()
    crud.update_user(db, target_user)
    return target_user
