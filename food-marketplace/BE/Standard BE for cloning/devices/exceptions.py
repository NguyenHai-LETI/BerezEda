from fastapi import HTTPException, status

# English error messages
DEVICE_NOT_FOUND_EN = "Device not found"
INVALID_PLATFORM_EN = "Invalid platform. Must be one of: ios, android, web"
DEVICE_TOKEN_EXISTS_EN = "Device token already exists"
UNAUTHORIZED_DEVICE_ACCESS_EN = "Unauthorized to access this device"

# Japanese error messages
DEVICE_NOT_FOUND_JP = "デバイスが見つかりません"
INVALID_PLATFORM_JP = (
    "無効なプラットフォームです。ios、android、webのいずれかを指定してください"
)
DEVICE_TOKEN_EXISTS_JP = "このデバイストークンは既に登録されています"
UNAUTHORIZED_DEVICE_ACCESS_JP = "このデバイスへのアクセス権限がありません"


def device_not_found():
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=DEVICE_NOT_FOUND_JP
    )


def invalid_platform():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_PLATFORM_JP
    )


def device_token_exists():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=DEVICE_TOKEN_EXISTS_JP
    )


def unauthorized_device_access():
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail=UNAUTHORIZED_DEVICE_ACCESS_JP
    )
