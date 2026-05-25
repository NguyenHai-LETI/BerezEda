from fastapi import HTTPException, status

from apps.users.constants import (
    ADMIN_ROLE_REQUIRED,
    CODE_EXPIRED,
    EMAIL_ALREADY_EXISTS,
    EMAIL_NOT_FOUND,
    EMAIL_REQUIRED,
    INSUFFICIENT_PERMISSIONS,
    INVALID_RESET_CODE,
    INVALID_SESSION_PURPOSE,
    INVALID_SESSION_TOKEN,
    INVALID_USER_TYPE,
    PASSWORDS_DO_NOT_MATCH,
    RATE_LIMIT_EXCEEDED,
    REDIS_UNAVAILABLE,
    UNAUTHORIZED_STAFF_REMOVAL,
    USER_NOT_FOUND,
    USERNAME_ALREADY_EXISTS,
    USERNAME_REQUIRED,
)


def insufficient_permissions(detail: str = INSUFFICIENT_PERMISSIONS):
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def user_not_found():
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=USER_NOT_FOUND)


def unauthorized_staff_removal():
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail=UNAUTHORIZED_STAFF_REMOVAL
    )


def email_already_exists():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=EMAIL_ALREADY_EXISTS
    )


def email_not_found():
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=EMAIL_NOT_FOUND)


def username_already_exists():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=USERNAME_ALREADY_EXISTS
    )


def invalid_user_type():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_USER_TYPE
    )


def admin_role_required():
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail=ADMIN_ROLE_REQUIRED
    )


def username_required():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=USERNAME_REQUIRED
    )


def email_required():
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=EMAIL_REQUIRED)


def redis_unavailable():
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=REDIS_UNAVAILABLE
    )


def passwords_do_not_match():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=PASSWORDS_DO_NOT_MATCH
    )


def rate_limit_exceeded():
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=RATE_LIMIT_EXCEEDED
    )


# New password reset flow exception functions
def invalid_reset_code():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_RESET_CODE
    )


def code_expired():
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=CODE_EXPIRED)


def invalid_session_token():
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail=INVALID_SESSION_TOKEN
    )


def invalid_session_purpose():
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail=INVALID_SESSION_PURPOSE
    )
