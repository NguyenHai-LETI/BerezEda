from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from apps.core.database import get_session
from apps.core.schemas import SuccessResponse, ListResponse
from apps.auth.permissions import CustomerUser, ShopOwnerOrAdminUser, AuthenticatedUserOrNone
from apps.reviews.models import Review
from apps.reviews.schemas import ReviewCreate, ReviewResponse

router = APIRouter(prefix="/reviews", tags=["Отзывы"])


@router.post("", response_model=SuccessResponse[ReviewResponse], status_code=201)
def create_review(body: ReviewCreate, current_user: CustomerUser, db: Session = Depends(get_session)):
    from apps.orders.crud import get_order_by_id
    from apps.orders.exceptions import order_not_found, order_access_denied

    order = get_order_by_id(db, body.order_id)
    if not order:
        raise order_not_found()
    if order.customer_id != current_user.id:
        raise order_access_denied()
    if order.status != "completed":
        raise HTTPException(status_code=400, detail="Отзыв можно оставить только после получения заказа")

    existing = db.exec(select(Review).where(Review.order_id == body.order_id)).first()
    if existing:
        raise HTTPException(status_code=409, detail="Отзыв на этот заказ уже оставлен")

    review = Review(
        order_id=body.order_id,
        customer_id=current_user.id,
        shop_id=order.shop_id,
        combo_id=order.combo_id,
        rating=body.rating,
        comment=body.comment,
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    # Update shop avg_rating and total_reviews
    try:
        from apps.shops.models import Shop
        shop = db.get(Shop, order.shop_id)
        if shop:
            all_reviews = db.exec(select(Review).where(Review.shop_id == order.shop_id)).all()
            shop.total_reviews = len(all_reviews)
            shop.avg_rating = round(sum(r.rating for r in all_reviews) / len(all_reviews), 2) if all_reviews else 0
            db.add(shop)
            db.commit()
    except Exception:
        pass

    return SuccessResponse(data=review, message="Отзыв оставлен")


@router.get("/order/{order_id}", response_model=SuccessResponse[ReviewResponse])
def get_review_for_order(order_id: str, current_user: CustomerUser, db: Session = Depends(get_session)):
    review = db.exec(select(Review).where(Review.order_id == order_id)).first()
    if not review or review.customer_id != current_user.id:
        return SuccessResponse[ReviewResponse](data=None, message="OK")
    return SuccessResponse[ReviewResponse](data=ReviewResponse.model_validate(review), message="OK")


@router.get("/shop/{shop_id}", response_model=ListResponse[ReviewResponse])
def get_shop_reviews(shop_id: str, user: AuthenticatedUserOrNone, db: Session = Depends(get_session)):
    reviews = db.exec(
        select(Review).where(Review.shop_id == shop_id).order_by(Review.created_at.desc())
    ).all()
    return ListResponse(data=reviews, total=len(reviews))


@router.get("/mine", response_model=ListResponse[ReviewResponse])
def get_my_shop_reviews(current_user: ShopOwnerOrAdminUser, db: Session = Depends(get_session)):
    from apps.shops.crud import get_shop_by_owner
    shop = get_shop_by_owner(db, current_user.id)
    if not shop:
        return ListResponse(data=[], total=0)
    reviews = db.exec(
        select(Review).where(Review.shop_id == shop.id).order_by(Review.created_at.desc())
    ).all()
    return ListResponse(data=reviews, total=len(reviews))
