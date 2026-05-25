from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from apps.auth.permissions import AuthenticatedUser
from apps.core.database import get_session
from apps.core.schemas import ListResponse, SuccessResponse

from . import schemas, services

router = APIRouter(tags=["Reviews"])


@router.get("/", response_model=ListResponse[schemas.ReviewDetailRead])
def list_reviews(
    user: AuthenticatedUser,
    db: Session = Depends(get_session),
    limit: Optional[int] = Query(None),
    offset: Optional[int] = Query(None),
):
    """List reviews with detailed nested data including user, shop, locker, and order information.
    If limit and offset are not provided, returns all reviews."""
    reviews, total = services.list_reviews_service(db, user, limit=limit, offset=offset)
    return ListResponse(
        limit=limit if limit is not None else total,
        offset=offset if offset is not None else 0,
        total=total,
        data=reviews,
    )


@router.get("/basic", response_model=ListResponse[schemas.ReviewRead])
def list_reviews_basic(user: AuthenticatedUser, db: Session = Depends(get_session)):
    """List reviews with basic data (for backwards compatibility)"""
    reviews, total = services.list_reviews_basic_service(db)
    return ListResponse(limit=20, offset=0, total=total, data=reviews)


@router.post("/", response_model=SuccessResponse[schemas.ReviewDetailRead])
def create_review(
    review: schemas.ReviewCreate,
    user: AuthenticatedUser,
    db: Session = Depends(get_session),
):
    """Create a new review and return detailed data"""
    review_obj = services.create_review_service(review, user.id, db)
    return SuccessResponse(data=review_obj)


@router.get("/{review_id}", response_model=SuccessResponse[schemas.ReviewDetailRead])
def get_review(
    review_id: str, user: AuthenticatedUser, db: Session = Depends(get_session)
):
    """Get review details with nested user, shop, locker, and order information"""
    review_obj = services.get_review_service(review_id, db)
    return SuccessResponse(data=review_obj)


@router.get("/{review_id}/basic", response_model=SuccessResponse[schemas.ReviewRead])
def get_review_basic(
    review_id: str, user: AuthenticatedUser, db: Session = Depends(get_session)
):
    """Get review with basic data (for backwards compatibility)"""
    review_obj = services.get_review_basic_service(review_id, db)
    return SuccessResponse(data=review_obj)


@router.put("/{review_id}", response_model=SuccessResponse[schemas.ReviewDetailRead])
def update_review(
    review_id: str,
    update: schemas.ReviewUpdate,
    user: AuthenticatedUser,
    db: Session = Depends(get_session),
):
    """Update review and return detailed data"""
    review_obj = services.update_review_service(review_id, db, update)
    return SuccessResponse(data=review_obj)


@router.delete("/{review_id}", response_model=SuccessResponse)
def delete_review(
    review_id: str, user: AuthenticatedUser, db: Session = Depends(get_session)
):
    """Delete review"""
    services.delete_review_service(review_id, db)
    return SuccessResponse(data=None)
