from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import and_, func, or_
from sqlmodel import Session, select

from apps.shops.models.shops import Shop
from apps.users.models.users import User


def get_user(db: Session, user_id: str):
    return db.get(User, user_id)


def create_user(db: Session, user: User):
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user: User):
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: User):
    user.is_active = False
    update_user(db, user)


def list_users(
    db: Session,
    limit: int,
    offset: int,
    permissions: Optional[List[str]] = None,
    name: Optional[str] = None,
):

    base_query = select(User).where(User.is_active == True)
    count_query = select(func.count()).select_from(User).where(User.is_active == True)

    if permissions:
        # Create OR conditions for multiple permissions
        if len(permissions) == 1:
            permission_filter = User.permissions == permissions[0]
        else:
            permission_conditions = []
            for perm in permissions:
                permission_conditions.append(User.permissions == perm)
            permission_filter = or_(*permission_conditions)

        base_query = base_query.where(permission_filter)
        count_query = count_query.where(permission_filter)

    if name:
        if permissions:
            if "customer" in permissions:
                name_filter = User.name.ilike(f"%{name}%")
            elif "owner_shop" in permissions or "owner_locker" in permissions:
                username_filter = User.name.ilike(f"%{name}%")
                name_conditions = [username_filter]
                if "owner_shop" in permissions:
                    shop_subquery = select(Shop.owner_id).where(
                        Shop.name.ilike(f"%{name}%")
                    )
                    shop_filter = User.id.in_(shop_subquery)
                    name_conditions.append(shop_filter)
                name_filter = or_(*name_conditions)

        base_query = base_query.where(name_filter)
        count_query = count_query.where(name_filter)

    total = db.exec(count_query).one()

    # Get paginated users with filter, ordered by created_at descending (newest first)
    statement = base_query.order_by(User.created_at.desc()).offset(offset).limit(limit)
    users = db.exec(statement).all()
    return users, total


def get_user_by_username(db: Session, username: str):
    statement = select(User).where(User.username == username, User.is_active.is_(True))
    return db.exec(statement).first()


def get_staff_by_shop_code(db: Session, shop_code: str, limit: int, offset: int):
    """
    Get staff users by shop code.

    Args:
        db: Database session
        shop_code: Shop code to filter staff by
        limit: Maximum number of results
        offset: Number of results to skip

    Returns:
        Tuple of (staff_list, total_count)
    """
    # Count total staff for this shop
    count_statement = (
        select(func.count())
        .select_from(User)
        .where(
            (User.code_shop == shop_code)
            & ((User.role == "staff_shop") | (User.role == "owner_shop"))
            & (User.permissions == "staff_shop")
            & (User.is_active == True)
        )
    )
    total = db.execute(count_statement).scalar() or 0

    # Get paginated staff list
    statement = (
        select(User)
        .where(
            (User.code_shop == shop_code)
            & ((User.role == "staff_shop") | (User.role == "owner_shop"))
            & (User.permissions == "staff_shop")
            & (User.is_active == True)
        )
        .offset(offset)
        .limit(limit)
    )

    result = db.execute(statement)
    staff_list = list(result.scalars().all())

    return staff_list, total


def get_all_shop_staff(db: Session, limit: int, offset: int):
    """
    Get all shop staff across all shops (admin only).

    Args:
        db: Database session
        limit: Maximum number of results
        offset: Number of results to skip

    Returns:
        Tuple of (staff_list, total_count)
    """
    # Count total shop staff
    count_statement = (
        select(func.count())
        .select_from(User)
        .where(
            ((User.role == "staff_shop") | (User.role == "owner_shop"))
            & (User.is_active == True)
        )
    )
    total = db.execute(count_statement).scalar() or 0

    # Get paginated staff list
    statement = (
        select(User)
        .where(
            ((User.role == "staff_shop") | (User.role == "owner_shop"))
            & (User.is_active == True)
        )
        .offset(offset)
        .limit(limit)
    )

    result = db.execute(statement)
    staff_list = list(result.scalars().all())

    return staff_list, total


def get_staff_by_shop_id(db: Session, shop_id: str):
    """
    Get all staff members for a specific shop ID.

    Args:
        db: Database session
        shop_id: Shop ID to filter staff by

    Returns:
        List of staff users
    """
    statement = select(User).where(
        (User.shop_id == shop_id)
        & (User.permissions == "staff_shop")
        & (User.is_active == True)
    )

    result = db.execute(statement)
    return list(result.scalars().all())


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    statement = select(User).where(User.email == email, User.is_active.is_(True))
    return db.exec(statement).first()


def update_user_password(
    db: Session, user_id: str, new_password_hash: str
) -> Optional[User]:
    statement = select(User).where(User.id == user_id)
    user = db.exec(statement).first()
    if user:
        user.password = new_password_hash
        user.updated_at = datetime.utcnow()
        user = update_user(db, user)
    return user


def get_staff_by_id(db: Session, staff_id: str) -> Optional[User]:
    statement = select(User).where(
        (User.id == staff_id)
        & (User.permissions == "staff_shop")
        & (User.is_active == True)
    )
    return db.exec(statement).first()


def delete_users_by_shop_code(db: Session, shop_code: str):
    """
    Soft delete all users by shop code (set is_active = False).

    Args:
        db: Database session
        shop_code: Shop code to filter users by
    """
    statement = select(User).where(User.code_shop == shop_code)
    users = db.exec(statement).all()
    for user in users:
        user.is_active = False
        db.add(user)
    db.commit()


def list_users_for_notification(
    db: Session,
    limit: int,
    offset: int,
    permission: Optional[List[str]] = None,
    email: Optional[str] = None,
    is_not_email: Optional[str] = None,
    phone_number: Optional[str] = None,
    is_not_phone_number: Optional[str] = None,
    is_exclude_birthday: bool = False,
    is_range_birthday: bool = False,
    is_lte_birthday_only: bool = False,
    is_gte_birthday_only: bool = False,
    birthday_date: Optional[date] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    town: Optional[str] = None,
    gender_values: Optional[List[str]] = None,
):
    """
    List users with advanced filtering for notification purposes.

    Args:
        db: Database session
        limit: Maximum number of results
        offset: Number of results to skip
        permission: List of permissions to filter by
        email: Email value to filter (partial match, case-insensitive)
        is_not_email: Email value to exclude (EXCLUDE match)
        phone_number: Phone value to filter (partial match, case-insensitive)
        is_not_phone_number: Phone value to exclude (EXCLUDE match)
        is_exclude_birthday: Whether to exclude the birthday_date (EXCLUDE mode)
        is_range_birthday: Whether to use date range filtering (RANGE mode)
        birthday_date: Parsed birthday date for EXACT/EXCLUDE mode
        start_date: Parsed start date for RANGE mode
        end_date: Parsed end date for RANGE mode
        town: Town name to search in address
        gender_values: List of gender values to filter by (already mapped from MALE/FEMALE)

    Returns:
        Tuple of (users_list, total_count)
    """
    # Base query
    base_query = select(User).where(User.is_active == True)
    count_query = select(func.count()).select_from(User).where(User.is_active == True)

    conditions = []

    if permission:
        if len(permission) == 1:
            permission_filter = User.role == permission[0]
        else:
            permission_conditions = [User.role == perm for perm in permission]
            permission_filter = or_(*permission_conditions)
        conditions.append(permission_filter)
    else:
        # only push notification for owner_shop or customer
        conditions.append(or_(User.role == "owner_shop", User.role == "customer"))

    if email:
        conditions.append(User.email.ilike(f"%{email}%"))
    elif is_not_email:
        conditions.append(User.email != is_not_email)

    if phone_number:
        conditions.append(User.phone.ilike(f"%{phone_number}%"))
    elif is_not_phone_number:
        # Exclude phone_number but include users with phone = null
        conditions.append(or_(User.phone != is_not_phone_number, User.phone.is_(None)))

    # Birthday filtering logic
    if is_range_birthday and start_date and end_date:
        # Both lte_birthday and gte_birthday provided: range filter
        conditions.append(and_(User.birthday >= start_date, User.birthday <= end_date))
    elif is_lte_birthday_only and end_date:
        # Only lte_birthday provided: birthday < lte_birthday
        conditions.append(User.birthday < end_date)
    elif is_gte_birthday_only and start_date:
        # Only gte_birthday provided: birthday > gte_birthday
        conditions.append(User.birthday > start_date)
    elif birthday_date:
        # EXACT or EXCLUDE mode
        if is_exclude_birthday:
            conditions.append(User.birthday != birthday_date)
        else:
            # EXACT match (default when birthday_date is provided)
            conditions.append(User.birthday == birthday_date)

    if town:
        conditions.append(User.address.ilike(f"%{town}%"))

    if gender_values:
        gender_conditions = [User.gender == val for val in gender_values]
        conditions.append(or_(*gender_conditions))

    # Apply all conditions
    if conditions:
        combined_condition = and_(*conditions)
        base_query = base_query.where(combined_condition)
        count_query = count_query.where(combined_condition)

    total = db.exec(count_query).one()

    statement = base_query.order_by(User.created_at.desc()).offset(offset).limit(limit)
    users = db.exec(statement).all()

    return users, total


def is_user_eligible_for_broadcast(db: Session, user_id: str) -> bool:
    """
    Check if user is eligible for broadcast notification.
    User is eligible if role is not 'admin' and not 'owner_locker'.

    Args:
        db: Database session
        user_id: User ID to check

    Returns:
        True if user is eligible, False otherwise
    """
    user = db.get(User, user_id)
    if not user:
        return False
    return user.role not in ["admin", "owner_locker"]
