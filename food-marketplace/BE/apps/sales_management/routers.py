from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from apps.core.utils import utcnow

from apps.core.database import get_session
from apps.core.schemas import SuccessResponse, ListResponse
from apps.auth.permissions import ShopOwnerOrAdminUser

router = APIRouter(prefix="/sales", tags=["Управление продажами"])


@router.get("/history", response_model=ListResponse)
def sales_history(
    date_str: Optional[str] = None,
    current_user: ShopOwnerOrAdminUser = ...,
    db: Session = Depends(get_session),
):
    from apps.shops.crud import get_shop_by_owner
    from apps.orders.models import Order
    from apps.combos.models import Combo

    shop = get_shop_by_owner(db, current_user.id)
    if not shop:
        return ListResponse(data=[], total=0)

    q = select(Order).where(Order.shop_id == shop.id, Order.status.in_(["paid", "completed"]))
    if date_str:
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            from sqlalchemy import extract
            q = q.where(
                extract("year", Order.created_at) == dt.year,
                extract("month", Order.created_at) == dt.month,
                extract("day", Order.created_at) == dt.day,
            )
        except Exception:
            pass
    orders = db.exec(q.order_by(Order.created_at.desc())).all()

    # Enrich with combo title
    combo_ids = list({o.combo_id for o in orders})
    combos_map: dict = {}
    if combo_ids:
        combos = db.exec(select(Combo).where(Combo.id.in_(combo_ids))).all()
        combos_map = {c.id: c.title for c in combos}

    result = []
    for o in orders:
        result.append({
            "id": o.id,
            "combo_id": o.combo_id,
            "combo_title": combos_map.get(o.combo_id, "Набор"),
            "amount": o.amount,
            "original_amount": o.original_amount,
            "discount_rate": o.discount_rate,
            "status": o.status,
            "created_at": o.created_at.isoformat(),
            "completed_at": o.completed_at.isoformat() if o.completed_at else None,
        })
    return ListResponse(data=result, total=len(result))


@router.get("/unsold", response_model=ListResponse)
def unsold_combos(current_user: ShopOwnerOrAdminUser, db: Session = Depends(get_session)):
    from apps.shops.crud import get_shop_by_owner
    from apps.combos.models import Combo

    shop = get_shop_by_owner(db, current_user.id)
    if not shop:
        return ListResponse(data=[], total=0)

    combos = db.exec(
        select(Combo).where(Combo.shop_id == shop.id, Combo.status == "expired")
        .order_by(Combo.sale_end_time.desc())
    ).all()
    return ListResponse(data=combos, total=len(combos))


@router.get("/summary", response_model=SuccessResponse)
def monthly_summary(
    year: Optional[int] = None,
    month: Optional[int] = None,
    current_user: ShopOwnerOrAdminUser = ...,
    db: Session = Depends(get_session),
):
    from apps.shops.crud import get_shop_by_owner
    from apps.orders.models import Order
    from apps.combos.models import Combo
    from sqlalchemy import extract

    now = utcnow()
    y = year or now.year
    m = month or now.month

    shop = get_shop_by_owner(db, current_user.id)
    if not shop:
        return SuccessResponse(data={
            "year": y, "month": m,
            "total_orders": 0, "total_revenue": 0,
            "food_saved_kg": 0, "co2_saved_kg": 0,
        })

    orders = db.exec(
        select(Order).where(
            Order.shop_id == shop.id,
            Order.status == "completed",
            extract("year", Order.created_at) == y,
            extract("month", Order.created_at) == m,
        )
    ).all()

    total_revenue = sum(o.amount for o in orders)
    combo_ids = [o.combo_id for o in orders]
    food_grams = 0
    if combo_ids:
        combos = db.exec(select(Combo).where(Combo.id.in_(combo_ids))).all()
        food_grams = sum(c.weight_grams for c in combos)

    food_saved_kg = round(food_grams / 1000, 2)
    co2_saved_kg = round(food_grams * 2.5 / 1000, 2)

    return SuccessResponse(data={
        "year": y, "month": m,
        "total_orders": len(orders),
        "total_revenue": total_revenue,
        "food_saved_kg": food_saved_kg,
        "co2_saved_kg": co2_saved_kg,
    })
