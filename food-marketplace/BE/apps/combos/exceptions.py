from fastapi import HTTPException, status

COMBO_NOT_FOUND_MSG = "Набор не найден"
COMBO_ACCESS_DENIED_MSG = "Нет доступа к этому набору"
COMBO_NOT_DRAFT_MSG = "Набор уже был опубликован"
COMBO_NOT_AVAILABLE_MSG = "Набор недоступен для покупки"
COMBO_UNIT_BUSY_MSG = "Этот бокс уже занят"
NO_PRODUCTS_MSG = "Добавьте хотя бы один товар в набор"


def combo_not_found():
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=COMBO_NOT_FOUND_MSG)

def combo_access_denied():
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=COMBO_ACCESS_DENIED_MSG)

def combo_not_draft():
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=COMBO_NOT_DRAFT_MSG)

def combo_not_available():
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=COMBO_NOT_AVAILABLE_MSG)

def no_products():
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=NO_PRODUCTS_MSG)

COMBO_NO_LOCKER_MSG = 'Не выбран постамат для набора'
COMBO_NOT_READY_MSG = 'Набор не готов к размещению'

def combo_no_locker():
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=COMBO_NO_LOCKER_MSG)

def combo_not_ready():
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=COMBO_NOT_READY_MSG)
