from fastapi import HTTPException, status

LOCKER_NOT_FOUND_MSG = "Ячейка не найдена"
LOCKER_UNIT_NOT_FOUND_MSG = "Бокс не найден"
LOCKER_UNIT_NOT_AVAILABLE_MSG = "Бокс недоступен"
LOCKER_ACCESS_DENIED_MSG = "Нет доступа к этой ячейке"
FAVORITE_LOCKER_NOT_FOUND_MSG = "Избранная ячейка не найдена"


def locker_not_found():
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=LOCKER_NOT_FOUND_MSG)

def locker_unit_not_found():
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=LOCKER_UNIT_NOT_FOUND_MSG)

def locker_unit_not_available():
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=LOCKER_UNIT_NOT_AVAILABLE_MSG)

def locker_access_denied():
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=LOCKER_ACCESS_DENIED_MSG)

def favorite_locker_not_found():
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=FAVORITE_LOCKER_NOT_FOUND_MSG)

LOCKER_UNIT_OCCUPIED_MSG = 'Нельзя удалить занятую ячейку'

def locker_unit_occupied():
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=LOCKER_UNIT_OCCUPIED_MSG)
