from fastapi import HTTPException

REVIEW_NOT_FOUND = "Review not found"
REVIEW_VALIDATION_ERROR = "Review validation failed"
REVIEW_COMMENT_REQUIRED = "口コミ投稿を入力してください。"


def review_not_found():
    return HTTPException(status_code=404, detail=REVIEW_NOT_FOUND)


def review_validation_error(message: str = REVIEW_VALIDATION_ERROR):
    return HTTPException(status_code=400, detail=message)


def review_comment_required():
    return HTTPException(status_code=400, detail=REVIEW_COMMENT_REQUIRED)
