from fastapi import HTTPException, status

COMBO_NOT_FOUND = "この商品はお店様都合でキャンセルされました。申し訳ございませんが、別の商品をご選択ください。"
PRODUCT_MASTER_NOT_FOUND = "Product not found"
PRODUCT_ALREADY_EXISTS = "既に登録済みです。同じ名前の商品は登録できません。"
PRODUCT_DELETE_FORBIDDEN = "この商品は他のコンボで使用されているため削除できません。"
INSUFFICIENT_PERMISSIONS = "権限がありません。"
SHOP_MANAGEMENT_REQUIRED = (
    "ショップの管理者、オーナー、またはスタッフである必要があります。"
)
COMBO_UPDATE_NOT_ALLOWED = "コンボの更新は許可されていません。"
COMBO_PRODUCTS_UPDATE_FORBIDDEN = "販売済みのコンボの商品は変更できません。"
PRODUCT_DELETE_ACTIVE_SALES_BLOCK = "【警告】\n    この商品は現在ロッカーで\n    販売中／支援中のため削除できません。\n    関連するすべての注文が完了または\n    販売時間終了されるまで\n    削除できません。\n                 [OK]   "

DRAFT_ALREADY_SALE_REGISTERED = "この下書きは 既に販売登録が 完了されました"
DRAFT_ALREADY_DELETED = "この下書きは削除されました。"
LOCKER_UNIT_ID_REQUIRED = "Locker unit id required when update draft"
PRODUCT_ALREADY_DELETED = (
    "選択した商品が存在しません。他のユーザに削除された可能性があります。"
)
COMBO_ALREADY_SOLD_CANNOT_CANCEL = (
    "この商品は既に他の方に購入されているため、キャンセルできません。"
)
COMBO_NOT_BELONG_TO_SHOP = "This combo does not belong to your shop. You cannot cancel combos from other shops."
COMBO_CANNOT_CANCEL_INVALID_STATUS = (
    "Only combos that are currently selling can be canceled."
)
COMBO_HAS_BEEN_PURCHASED = "この商品は既に他の方に購入されているため、編集できません。"
COMBO_HAS_BEEN_EDITED = "店舗側でこの商品の内容が変更されました。お手数ですが詳細画面に戻ってご確認ください。"


def combo_not_found():
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=COMBO_NOT_FOUND)


def product_master_not_found():
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=PRODUCT_MASTER_NOT_FOUND
    )


def product_master_already_deleted():
    return HTTPException(
        status_code=status.HTTP_410_GONE, detail=PRODUCT_ALREADY_DELETED
    )


def product_already_exists():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=PRODUCT_ALREADY_EXISTS
    )


def product_delete_forbidden():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=PRODUCT_DELETE_FORBIDDEN
    )


def product_delete_blocked_active_sales():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=PRODUCT_DELETE_ACTIVE_SALES_BLOCK,
    )


def insufficient_permissions(detail: str = INSUFFICIENT_PERMISSIONS):
    """Generic insufficient permissions exception"""
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def shop_management_required():
    """Exception for when shop management permissions are required"""
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail=SHOP_MANAGEMENT_REQUIRED
    )


def combo_update_not_allowed(detail: str = COMBO_UPDATE_NOT_ALLOWED):
    """Exception for when combo cannot be updated due to status or business rules"""
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def combo_products_update_forbidden():
    """Exception for when trying to update products of a sold combo"""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=COMBO_PRODUCTS_UPDATE_FORBIDDEN
    )


def draft_already_sale_registered():
    """Draft was already registered for sale by another user"""
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT, detail=DRAFT_ALREADY_SALE_REGISTERED
    )


def draft_already_deleted():
    """Draft was already deleted by another user"""
    return HTTPException(status_code=status.HTTP_410_GONE, detail=DRAFT_ALREADY_DELETED)


def locker_unit_id_required():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=LOCKER_UNIT_ID_REQUIRED
    )


def combo_already_sold_cannot_cancel():
    """Exception for when trying to cancel a combo that has already been sold"""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=COMBO_ALREADY_SOLD_CANNOT_CANCEL
    )


def combo_not_belong_to_shop():
    """Exception for when shop owner tries to cancel a combo from another shop"""
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail=COMBO_NOT_BELONG_TO_SHOP
    )


def combo_cannot_cancel_invalid_status(combo_status: str):
    """Exception for when trying to cancel a combo that is not in SELLING status"""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"ステータス '{combo_status}' のコンボはキャンセルできません。販売中のコンボのみキャンセルできます。",
    )


def combo_has_been_purchased():
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=COMBO_HAS_BEEN_PURCHASED
    )


def combo_has_been_edited():
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT, detail=COMBO_HAS_BEEN_EDITED
    )
