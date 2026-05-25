from datetime import datetime

from sqlalchemy import and_, or_
from sqlmodel import Session, select

from apps.core.celery_app import celery_app
from apps.core.constants import ORDER_STATUS_PICKED_UP
from apps.core.database import engine
from apps.core.logging import logger
from apps.core.utils import get_current_time
from apps.orders.models import Order
from apps.products.crud import get_combo_with_product_masters


@celery_app.task
def shop_index_update_firebase_task(shop_id: str):
    """Calculate shop's month-to-date food loss reduction and sync to Firebase."""
    try:
        from apps.integrations.firebase.shop_service import FirebaseShopService

        with Session(engine) as db:
            current_time = get_current_time()
            # Get start of current month
            month_start = datetime(current_time.year, current_time.month, 1)
            # Get start of next month
            if current_time.month == 12:
                month_end = datetime(current_time.year + 1, 1, 1)
            else:
                month_end = datetime(current_time.year, current_time.month + 1, 1)

            # Get all picked up orders for this shop in current month
            picked_up_orders = db.exec(
                select(Order)
                .where(Order.shop_id == shop_id)
                .where(Order.status == ORDER_STATUS_PICKED_UP)
                .where(
                    or_(
                        # Case 1
                        and_(
                            Order.picked_up_at.isnot(None),
                            Order.picked_up_at >= month_start,
                            Order.picked_up_at < month_end,
                        ),
                        # Case 2
                        and_(
                            Order.picked_up_at.is_(None),
                            Order.completed_at >= month_start,
                            Order.completed_at < month_end,
                        ),
                    )
                )
            ).all()

            total_food_waste = 0
            total_revenue_this_month = 0
            for order in picked_up_orders:
                total_revenue_this_month += (
                    order.final_price if order.final_price else 0.0
                )
                # Get combo with product relationships
                full_combo = get_combo_with_product_masters(db, order.combo_id)
                if not full_combo or not full_combo.combo_products:
                    continue

                for combo_product in full_combo.combo_products:
                    if (
                        combo_product.product_master
                        and hasattr(combo_product.product_master, "food_waste_weight")
                        and combo_product.product_master.food_waste_weight
                    ):
                        product_waste = (
                            combo_product.product_master.food_waste_weight
                            * combo_product.quantity
                        )
                        total_food_waste += int(product_waste)

            # Prepare data for Firebase
            food_loss_data = {
                "food_loss_reduction_this_month": total_food_waste,
                "total_combo_sold_this_month": len(picked_up_orders),
                "food_loss_updated_at": current_time.isoformat(),
                "total_revenue_this_month": total_revenue_this_month,
                "revenue_updated_at": current_time.isoformat(),
            }

        # Update shop stats in Firebase
        firebase_service = FirebaseShopService()
        result = firebase_service.update_shop_in_firebase(shop_id, food_loss_data)

        if result:
            logger.info(
                f"Successfully updated food loss reduction for shop {shop_id}: {total_food_waste}g"
            )
        else:
            logger.error(f"Failed to update food loss for shop {shop_id} to Firebase")

        return result

    except Exception as e:
        logger.error(f"Error in update_shop_food_loss_to_firebase_task: {e}")
        return False
