from fastapi import HTTPException, status

SHOP_NOT_FOUND_MSG = "Магазин не найден"
SHOP_ALREADY_EXISTS_MSG = "У вас уже есть магазин"
SHOP_ACCESS_DENIED_MSG = "Нет доступа к этому магазину"


def shop_not_found():
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=SHOP_NOT_FOUND_MSG)


def shop_already_exists():
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=SHOP_ALREADY_EXISTS_MSG)


def shop_access_denied():
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=SHOP_ACCESS_DENIED_MSG)
