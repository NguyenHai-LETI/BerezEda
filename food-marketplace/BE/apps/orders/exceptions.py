from fastapi import HTTPException, status

ORDER_NOT_FOUND_MSG = "Заказ не найден"
ORDER_ACCESS_DENIED_MSG = "Нет доступа к этому заказу"
ORDER_ALREADY_PAID_MSG = "Заказ уже оплачен"
ORDER_NOT_PAID_MSG = "Заказ не оплачен"
ORDER_PICKUP_EXPIRED_MSG = "Время получения заказа истекло"
COMBO_ALREADY_SOLD_MSG = "Этот набор уже куплен"


def order_not_found():
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ORDER_NOT_FOUND_MSG)

def order_access_denied():
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ORDER_ACCESS_DENIED_MSG)

def order_already_paid():
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=ORDER_ALREADY_PAID_MSG)

def order_not_paid():
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ORDER_NOT_PAID_MSG)

def order_pickup_expired():
    return HTTPException(status_code=status.HTTP_410_GONE, detail=ORDER_PICKUP_EXPIRED_MSG)

def combo_already_sold():
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=COMBO_ALREADY_SOLD_MSG)

WRONG_ACCESS_CODE_MSG = 'Неверный код доступа'

def wrong_access_code():
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=WRONG_ACCESS_CODE_MSG)
