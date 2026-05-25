from fastapi import HTTPException, status

from apps.purchase.constants import *


def user_already_registered():
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=USER_ALREADY_REGISTERED
    )


def user_not_found_db_or_fincode():
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=USER_NOT_FOUND_DB_OR_FINCODE
    )


def executed_payment_not_found():
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT, detail=EXECUTED_PAYMENT_NOT_FOUND
    )


def invalid_order_information():
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_ORDER_INFORMATION
    )


def card_registration_limit_exceeded():
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=CARD_REGISTRATION_LIMIT_EXCEEDED
    )


def payment_not_found_for_order():
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Payment or access_id not found for the given order_id.",
    )


def invalid_card_owner():
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail=INVALID_CARD_OWNER
    )


def payment_already_success_making():
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Payment has already been made for this order.",
    )
