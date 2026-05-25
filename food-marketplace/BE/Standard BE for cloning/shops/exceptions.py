from fastapi import HTTPException, status

from apps.shops.constants import (
    SHOP_ALREADY_EXISTS,
    SHOP_NOT_FOUND,
    UNAUTHORIZED_SHOP_REMOVAL,
)


def shop_not_found():
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=SHOP_NOT_FOUND)


def shop_already_exists():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=SHOP_ALREADY_EXISTS
    )


def unauthorized_shop_removal():
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail=UNAUTHORIZED_SHOP_REMOVAL
    )
