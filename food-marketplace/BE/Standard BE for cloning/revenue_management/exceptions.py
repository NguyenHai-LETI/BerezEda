from fastapi import HTTPException, status

from apps.revenue_management.constants import (
    INVALID_TIME_DURATION,
    TOTAL_MISMATCH_ERROR,
)


def total_mismatch_exception():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=TOTAL_MISMATCH_ERROR
    )


def invalid_duration_exception():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_TIME_DURATION
    )


def no_accessible_shops_exception():
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="アクセス可能な店舗が見つかりません。",
    )


def invalid_filter_params_exception():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="locker_idsまたはshop_idsのいずれか一方のみを指定してください。",
    )


def invalid_metric_exception():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="metricはCUSTOMER_COUNTまたはREVENUEのいずれかを指定してください。",
    )


def invalid_segment_exception():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="segmentはONE_TIMEまたはRETURNINGのいずれかを指定してください。",
    )
