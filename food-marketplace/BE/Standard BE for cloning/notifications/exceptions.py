from fastapi import HTTPException, status

# Error code constants
NOTIFICATION_NOT_FOUND = "通知が見つかりません。"
NOTIFICATION_USER_NOT_FOUND = "NotificationUser not found"


def notification_not_found():
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=NOTIFICATION_NOT_FOUND
    )


def notification_user_not_found():
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=NOTIFICATION_USER_NOT_FOUND
    )
