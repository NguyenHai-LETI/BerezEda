from fastapi import HTTPException, status

from apps.favorites.constants import FAVORITE_ALREADY_EXISTS, FAVORITE_NOT_FOUND


def favorite_not_found():
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=FAVORITE_NOT_FOUND
    )


def favorite_already_exists():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=FAVORITE_ALREADY_EXISTS
    )
