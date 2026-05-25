from fastapi import HTTPException, status

# Error Messages
LOCKER_LOCATION_NOT_FOUND = "ロッカーの場所が見つかりません"
LOCKER_UNIT_NOT_FOUND = "ロッカーユニットが見つかりません"
LOCKER_RESERVATION_NOT_FOUND = "ロッカーの予約が見つかりません"
LOCKER_UNIT_NOT_AVAILABLE = "ロッカーユニットは利用できません"
LOCKER_UNIT_ALREADY_OCCUPIED = "ロッカーユニットは既に使用中です"
INVALID_RESERVATION_TIME = "無効な予約時間です"
OVERLAPPING_RESERVATION = "予約時間が既存の予約と重複しています"
RESERVATION_NOT_ACTIVE = "予約がアクティブではありません"
ACCESS_CODE_INVALID = "無効なアクセスコードです"
UNAUTHORIZED_SHOP_ACCESS = "ショップのロッカーシステムへの不正アクセスです"
INSUFFICIENT_PERMISSIONS = "権限がありません"
SHOP_MANAGEMENT_REQUIRED = (
    "ショップの管理者、オーナー、またはスタッフである必要があります"
)

OWNER_LOCKER_ID_REQUIRED = "owner_id parameter is required for admin users"
USER_HAS_ACTIVE_RESERVATION = "あなたには既にアクティブな予約があります。現在の予約の準備期限が過ぎるまでお待ちください。"
USER_CANNOT_BOOK_DIFFERENT_LOCKER = "あなたには既にアクティブな予約があります。別のロッカーを予約することはできません。現在予約中のロッカーのみ再確認できます。"
CHANGING_LOCKER_UNIT_ID_NOT_ALLOWED = "ロッカーユニットIDの変更は許可されていません。別のユニットを選択する必要があります。"
LOCKER_UNIT_EMPTY = "ロッカーユニットは空です"
LOCKER_UNIT_TOPIC_NAME_MISSING = "Locker unit topic name is not configured"

# Favorite locker (My Locker) errors
FAVORITE_LOCKER_LIMIT_REACHED = "You can add at most 3 favorite lockers"
FAVORITE_LOCKER_NOT_FOUND = "Favorite locker not found"
FAVORITE_LOCKER_REORDER_INVALID = (
    "locker_location_ids must match exactly the current favorites"
)


def favorite_locker_limit_reached():
    """User already has 3 favorite lockers."""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=FAVORITE_LOCKER_LIMIT_REACHED
    )


def favorite_locker_not_found():
    """Favorite locker not in user's list."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=FAVORITE_LOCKER_NOT_FOUND
    )


def favorite_locker_reorder_invalid():
    """Reorder request invalid: ids do not match current favorites."""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=FAVORITE_LOCKER_REORDER_INVALID,
    )


def locker_location_not_found():
    """Locker location not found exception"""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=LOCKER_LOCATION_NOT_FOUND
    )


def locker_unit_not_found():
    """Locker unit not found exception"""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=LOCKER_UNIT_NOT_FOUND
    )


def locker_reservation_not_found():
    """Locker reservation not found exception"""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=LOCKER_RESERVATION_NOT_FOUND
    )


def reservation_expired():
    """Locker reservation expired exception"""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="ロッカーの商品預入れ時間が期限切れになりました",
    )


def locker_unit_not_available():
    """Locker unit not available exception"""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=LOCKER_UNIT_NOT_AVAILABLE
    )


def locker_unit_already_occupied():
    """Locker unit already occupied exception"""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=LOCKER_UNIT_ALREADY_OCCUPIED
    )


def locker_unit_empty():
    """Locker unit empty exception"""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=LOCKER_UNIT_EMPTY
    )


def invalid_reservation_time():
    """Invalid reservation time exception"""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_RESERVATION_TIME
    )


def overlapping_reservation():
    """Overlapping reservation exception"""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=OVERLAPPING_RESERVATION
    )


def reservation_not_active():
    """Reservation not active exception"""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=RESERVATION_NOT_ACTIVE
    )


def access_code_invalid():
    """Access code invalid exception"""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=ACCESS_CODE_INVALID
    )


def unauthorized_shop_access():
    """Unauthorized shop access exception"""
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail=UNAUTHORIZED_SHOP_ACCESS
    )


def insufficient_permissions(detail: str = INSUFFICIENT_PERMISSIONS):
    """Generic insufficient permissions exception"""
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def shop_management_required():
    """Shop management required exception"""
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail=SHOP_MANAGEMENT_REQUIRED
    )


def owner_locker_id_required():
    return HTTPException(status_code=400, detail=OWNER_LOCKER_ID_REQUIRED)


def user_has_active_reservation():
    """User already has an active reservation exception"""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=USER_HAS_ACTIVE_RESERVATION
    )


def user_cannot_book_different_locker():
    """User cannot book different locker when having active reservation"""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=USER_CANNOT_BOOK_DIFFERENT_LOCKER,
    )


def changing_locker_unit_id_not_allowed():
    """Changing locker_unit_id is not allowed exception"""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=CHANGING_LOCKER_UNIT_ID_NOT_ALLOWED,
    )


def locker_unit_topic_name_missing():
    """Locker unit topic name is missing exception"""
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=LOCKER_UNIT_TOPIC_NAME_MISSING,
    )

COLUMN_INDEX_OUT_OF_RANGE = "column_index must be between 1 and {max_col}"
LOCKER_UNITS_NOT_FOUND_FOR_COLUMN = "No locker units found with column_index={column_index} in this location"
TEMPERATURE_OUT_OF_RANGE = "temperature must be between -20 and 15 degrees, got {temperature}"
TEMPERATURE_NOT_NUMERIC = "temperature must be a numeric value, got '{temperature}'"


def column_index_out_of_range(max_col: int):
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=COLUMN_INDEX_OUT_OF_RANGE.format(max_col=max_col),
    )


def locker_units_not_found_for_column(column_index: int):
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=LOCKER_UNITS_NOT_FOUND_FOR_COLUMN.format(column_index=column_index),
    )


def temperature_out_of_range(temperature: str):
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=TEMPERATURE_OUT_OF_RANGE.format(temperature=temperature),
    )


def temperature_not_numeric(temperature: str):
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=TEMPERATURE_NOT_NUMERIC.format(temperature=temperature),
    )
