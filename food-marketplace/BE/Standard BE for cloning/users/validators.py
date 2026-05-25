from datetime import date, datetime
from typing import Optional, Tuple, Union

from sqlmodel import Session

from apps.core.config import (
    FORGOT_PASSWORD_EMAIL_LIMIT,
    FORGOT_PASSWORD_EMAIL_WINDOW,
    RESET_PASSWORD_LIMIT,
    RESET_PASSWORD_WINDOW,
)
from apps.integrations.redis.redis_service import check_rate_limit_service
from apps.users import crud, schemas
from apps.users.exceptions import (
    email_already_exists,
    email_required,
    invalid_user_type,
    passwords_do_not_match,
    rate_limit_exceeded,
    unauthorized_staff_removal,
    user_not_found,
    username_already_exists,
)
from apps.users.models.users import User


def validate_username_uniqueness(username: str, db: Session) -> None:
    """Validate that username is unique in the database."""
    db_user = crud.get_user_by_username(db, username)
    if db_user:
        raise username_already_exists()


def validate_email_uniqueness(email: str, db: Session) -> None:
    """Validate that email is unique in the database."""
    db_user = crud.get_user_by_email(db, email)
    if db_user and db_user.is_active:
        raise email_already_exists()


def validate_user_role(role: str) -> None:
    """Validate that the user role is valid."""
    allowed_roles = ["customer", "admin", "owner_locker", "owner_shop"]
    if role not in allowed_roles:
        raise invalid_user_type()


def validate_user_uniqueness_by_role(
    username: str | None, email: str | None, role: str, db: Session
) -> None:
    """Validate user uniqueness based on role requirements."""
    if not email:
        raise email_required()
    validate_email_uniqueness(email, db)

    if role == "customer" and username is not None:
        validate_username_uniqueness(username, db)
    else:
        validate_user_role(role)


def get_default_permissions_by_role(role: str) -> str:
    """Get default permissions based on user role."""
    permission_mapping = {
        "admin": "admin",
        "customer": "customer",
        "owner_shop": "owner_shop",
        "owner_locker": "owner_locker",
    }
    return permission_mapping.get(role, "customer")


def validate_permissions(permissions: str) -> None:
    """Validate that all permissions are valid."""
    valid_permissions = [
        "Administrator",
        "admin",
        "owner_locker",
        "owner_shop",
        "staff_shop",
        "customer",
    ]
    # For string permissions, check the whole string
    if permissions not in valid_permissions:
        raise ValueError(f"Invalid permission: {permissions}")


def set_user_permissions(user_data: dict, role: str) -> dict:
    """Set user permissions based on role if not explicitly provided."""
    if "permissions" not in user_data or not user_data["permissions"]:
        user_data["permissions"] = get_default_permissions_by_role(role)
    else:
        validate_permissions(user_data["permissions"])
    return user_data


def validate_user_uniqueness(
    user: Union[schemas.UserCreate, schemas.StaffCreate], db: Session
) -> None:
    """Validate that username/email doesn't already exist based on user role."""
    # Handle username for different schema types
    username = getattr(user, "username", None)

    validate_user_uniqueness_by_role(
        username=username,
        email=str(user.email),  # Email is now required for all users
        role=user.role,
        db=db,
    )


def validate_password_match(password: str, confirm_password: str) -> None:
    if password != confirm_password:
        raise passwords_do_not_match()


def validate_staff_removal_permission(
    staff_user: User | None, requesting_user: User
) -> None:
    """Validate that user has permission to remove staff member."""
    if not staff_user:
        raise user_not_found()
    if (
        requesting_user.permissions == "owner_shop"
        and staff_user.code_shop != requesting_user.code_shop
    ):
        raise unauthorized_staff_removal()


def validate_user_exists(user: User | None) -> None:
    if not user:
        raise user_not_found()


def validate_shop_owner_permissions(user: User) -> bool:
    """Validate that user is shop owner with proper shop setup."""
    if user.role == "owner_shop":
        associated_shop = user.get_associated_shop()
        if not associated_shop or not associated_shop.code:
            return False
    return True


def validate_forgot_password_rate_limit(email: str, redis_client) -> None:
    """Check rate limit for forgot password endpoint - only per email."""
    email_key = f"rate_limit:forgot_password:email:{email}"
    if not check_rate_limit_service(
        email_key,
        limit=FORGOT_PASSWORD_EMAIL_LIMIT,
        window=FORGOT_PASSWORD_EMAIL_WINDOW,
        client=redis_client,
    ):
        raise rate_limit_exceeded()


def validate_reset_password_rate_limit(session_token: str, redis_client) -> None:
    session_key = f"rate_limit:reset_password:session:{session_token[-10:]}"
    if not check_rate_limit_service(
        session_key,
        limit=RESET_PASSWORD_LIMIT,
        window=RESET_PASSWORD_WINDOW,
        client=redis_client,
    ):
        raise rate_limit_exceeded()


def validate_staff_belong_to_shop(staff: User, shop: User) -> bool:
    """Validate that staff belongs to shop."""
    return staff.code_shop == shop.code_shop


def validate_and_parse_birthday_fields(
    e_birthday: Optional[str] = None,
    is_not_birthday: Optional[str] = None,
    lte_birthday: Optional[str] = None,
    gte_birthday: Optional[str] = None,
) -> Tuple[Optional[date], Optional[date], Optional[date]]:
    """
    Validate and parse birthday-related fields for query filtering.

    Args:
        e_birthday: Birthday value in YYYY-MM-DD format for EXACT match
        is_not_birthday: Birthday value in YYYY-MM-DD format for EXCLUDE match
        lte_birthday: Start date in YYYY-MM-DD format for RANGE mode
        gte_birthday: End date in YYYY-MM-DD format for RANGE mode

    Returns:
        Tuple of (birthday_date, start_date, end_date) where:
        - birthday_date: Parsed date for EXACT/EXCLUDE mode
        - start_date: Parsed start date for RANGE mode
        - end_date: Parsed end date for RANGE mode

    Raises:
        ValueError: If validation fails
    """
    # Initialize return values
    birthday_date = None
    start_date = None
    end_date = None

    # Determine which mode based on provided parameters
    is_range_mode = bool(lte_birthday or gte_birthday)
    is_exact_mode = bool(e_birthday)
    is_exclude_mode = bool(is_not_birthday)

    # Validate that date range parameters don't conflict with exact/exclude mode
    if is_range_mode:
        if is_exact_mode or is_exclude_mode:
            raise ValueError(
                "Cannot provide e_birthday/is_not_birthday together with lte_birthday/gte_birthday"
            )
        # Parse lte_birthday if provided
        if lte_birthday:
            try:
                end_date = datetime.strptime(lte_birthday, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError("lte_birthday must be in YYYY-MM-DD format")
        # Parse gte_birthday if provided
        if gte_birthday:
            try:
                start_date = datetime.strptime(gte_birthday, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError("gte_birthday must be in YYYY-MM-DD format")
        return None, start_date, end_date

    # EXACT or EXCLUDE mode
    birthday = e_birthday if is_exact_mode else is_not_birthday
    if birthday:
        try:
            birthday_date = datetime.strptime(birthday, "%Y-%m-%d").date()
            return birthday_date, None, None
        except ValueError:
            raise ValueError("birthday must be in YYYY-MM-DD format")

    return None, None, None


def validate_notification_user_filters(
    email: Optional[str] = None,
    is_not_email: Optional[str] = None,
    phone_number: Optional[str] = None,
    is_not_phone_number: Optional[str] = None,
    e_birthday: Optional[str] = None,
    is_not_birthday: Optional[str] = None,
    lte_birthday: Optional[str] = None,
    gte_birthday: Optional[str] = None,
    gender: Optional[str] = None,
) -> None:
    """
    Validate filter parameters for notification user listing.

    Args:
        email: Email value to filter
        is_not_email: Email value to exclude
        phone_number: Phone value to filter
        is_not_phone_number: Phone value to exclude
        e_birthday: Birthday value for EXACT match
        is_not_birthday: Birthday value for EXCLUDE match
        lte_birthday: Birthday start date for RANGE mode
        gte_birthday: Birthday end date for RANGE mode
        gender: Gender value (MALE or FEMALE)

    Raises:
        ValueError: If any validation fails
    """
    # Validate that email and is_not_email are not both provided
    if email and is_not_email:
        raise ValueError("Cannot provide both email and is_not_email parameters")

    # Validate that phone_number and is_not_phone_number are not both provided
    if phone_number and is_not_phone_number:
        raise ValueError(
            "Cannot provide both phone_number and is_not_phone_number parameters"
        )

    # Validate that e_birthday and is_not_birthday are not both provided
    if e_birthday and is_not_birthday:
        raise ValueError(
            "Cannot provide both e_birthday and is_not_birthday parameters"
        )

    # Validate that e_birthday/is_not_birthday and date range are not both provided
    if (e_birthday or is_not_birthday) and (lte_birthday or gte_birthday):
        raise ValueError(
            "Cannot provide e_birthday/is_not_birthday together with lte_birthday/gte_birthday"
        )

    if gender and gender.lower() not in ["male", "female", "other"]:
        raise ValueError("gender must be male, female, or other")
