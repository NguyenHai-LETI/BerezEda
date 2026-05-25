from fastapi import HTTPException, status

# Error Messages
QRCODE_NOT_FOUND = "QR code not found."
QRCODE_ALREADY_USED = "この二次元コードは利用済みです。"
QRCODE_INACTIVE = "The QR code is inactive."
QRCODE_CANNOT_DELETE_USED = "Used QR codes cannot be deleted."
USER_ALREADY_VERIFIED = (
    "既にアカウント認証は完了しています。引き続きアプリをご利用ください。"
)
INVALID_QRCODE = "QRコードは無効です。"


def qrcode_not_found():
    """QR code not found exception"""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=QRCODE_NOT_FOUND)


def qrcode_already_used():
    """QR code already used exception"""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=QRCODE_ALREADY_USED
    )


def qrcode_inactive():
    """QR code inactive exception"""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=QRCODE_INACTIVE
    )


def qrcode_cannot_delete_used():
    """QR code cannot delete used exception"""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=QRCODE_CANNOT_DELETE_USED
    )


def user_already_verified():
    """User already verified QR code exception"""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=USER_ALREADY_VERIFIED
    )
