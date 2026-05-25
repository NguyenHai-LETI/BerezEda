"""
Order-related exceptions
"""

from fastapi import HTTPException, status


def order_not_found():
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
    )


def combo_not_available_for_purchase():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="先に他のユーザーが購入手続きを進めています。",
    )


def app_version_too_old():
    raise HTTPException(
        status_code=status.HTTP_426_UPGRADE_REQUIRED,
        detail="このアプリの新しいバージョンが必要です。アップデートを行ってからご利用ください。",
    )


def wrong_data():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Data edited_at wrong. Please check again",
    )


def invalid_order_status():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="先に他のユーザーが購入手続きを進めています。",
    )


def combo_expired_time_sales():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="こちらの商品の販売時間が終了致しました。別の商品をお選びください。",
    )


def order_already_completed():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Order has already been completed",
    )


def order_already_refunded():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Order has already been refunded",
    )


def order_cannot_be_cancelled():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Order cannot be cancelled in its current status",
    )


def invalid_pickup_code():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid pickup code"
    )


def order_expired():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="Order has expired"
    )


def insufficient_funds():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Insufficient funds for this purchase",
    )


def mynaportal_linking_required():
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="MyNa Portal account linking is required to access free combos for needy people",
    )


def purchase_in_progress():
    """Raised when another user has already started the purchase flow for the combo."""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="先に他のユーザーが購入手続きを進めています。",
    )


def insufficient_permission_for_free_product():
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to purchase free products",
    )


def fail_payment():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Payment failed",
    )


def free_combo_cooldown_not_met():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=(
            "支援の受け取りは1回まで可能です。\n"
            "一度受け取りを行った場合、受け取り後から2時間経過すると\n"
            "再度受け取りが可能になります。"
        ),
    )


def order_picked_up():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="商品を受け取ったため、キャンセルはできません。",
    )


def combo_data_changed():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="店舗側でこの商品の内容が変更されました。お手数ですが詳細画面に戻ってご確認ください。",
    )
