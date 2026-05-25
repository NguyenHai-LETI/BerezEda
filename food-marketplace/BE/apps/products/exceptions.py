from fastapi import HTTPException, status

PRODUCT_NOT_FOUND_MSG = "Товар не найден"
PRODUCT_ACCESS_DENIED_MSG = "Нет доступа к этому товару"


def product_not_found():
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=PRODUCT_NOT_FOUND_MSG)


def product_access_denied():
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=PRODUCT_ACCESS_DENIED_MSG)
