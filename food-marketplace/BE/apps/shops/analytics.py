"""
Shop Analytics Service

This module provides analytics functions to calculate shop metrics for Firebase sync.
"""

from datetime import datetime, timezone
from typing import Any, Dict

from sqlmodel import Session, col, func, select

from apps.core.constants import (
    COMBO_STATUS_DRAFT,
    COMBO_STATUS_PREPARATION_TO_LOCKER,
    ORDER_STATUS_PICKED_UP,
    ORDER_STATUS_READY_FOR_PICKUP,
    ORDER_STATUS_REFUNDED,
    REVENUE_COUNTABLE_ORDER_STATUSES,
)
from apps.core.utils import get_current_time_utc
from apps.orders.models.orders import Order

# Legacy constants for backward compatibility
COMBO_STATUS_LOCKER_RESERVED = COMBO_STATUS_PREPARATION_TO_LOCKER  # Legacy alias
COMBO_STATUS_PICKED_UP = ORDER_STATUS_PICKED_UP  # This should reference ORDER status
from apps.products.models.combos import Combo


def get_shop_analytics_for_firebase(db: Session, shop_id: str) -> Dict[str, Any]:
    """
    Calculate shop analytics for Firebase sync.

    Returns:
        Dict containing:
        - free_products_this_month: Number of free products distributed this month
        - food_loss_reduction_this_month: Total food loss reduction this month
        - pending_support_products: Products registered but not yet in locker
    """
    # Get current month start date
    now = get_current_time_utc()
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    # 1. Number of products distributed for free this month (picked up)
    free_products_query = select(func.count(col(Combo.id))).where(
        col(Combo.shop_id) == shop_id,
        col(Combo.status) == COMBO_STATUS_PICKED_UP,
        col(Combo.original_price) == 0.0,  # Free products
        col(Combo.updated_at) >= month_start,
    )
    free_products_this_month = db.exec(free_products_query).first() or 0

    # 2. Total food loss reduction (all picked up products this month)
    # This represents total value of food that was saved from being wasted
    food_loss_query = select(
        func.coalesce(func.sum(col(Combo.original_price)), 0)
    ).where(
        col(Combo.shop_id) == shop_id,
        col(Combo.status) == COMBO_STATUS_PICKED_UP,
        col(Combo.updated_at) >= month_start,
    )
    food_loss_reduction_this_month = db.exec(food_loss_query).first() or 0.0

    # 3. Products registered for support but not yet added to locker
    # These are products in draft or locker_reserved status
    pending_support_query = select(func.count(col(Combo.id))).where(
        col(Combo.shop_id) == shop_id,
        col(Combo.status).in_([COMBO_STATUS_DRAFT, COMBO_STATUS_LOCKER_RESERVED]),
    )
    pending_support_products = db.exec(pending_support_query).first() or 0

    # 4. Month-to-date revenue
    total_revenue_this_month = get_month_to_date_revenue(db, shop_id)

    return {
        "free_products_this_month": int(free_products_this_month),
        "food_loss_reduction_this_month": float(food_loss_reduction_this_month),
        "pending_support_products": int(pending_support_products),
        "month_to_date_revenue": float(total_revenue_this_month),
        "analytics_updated_at": get_current_time_utc().isoformat(),
    }


def get_monthly_free_products_count(db: Session, shop_id: str) -> int:
    """Get count of free products distributed this month."""
    now = get_current_time_utc()
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    query = select(func.count(col(Combo.id))).where(
        col(Combo.shop_id) == shop_id,
        col(Combo.status) == COMBO_STATUS_PICKED_UP,
        col(Combo.original_price) == 0.0,
        col(Combo.updated_at) >= month_start,
    )

    return db.exec(query).first() or 0


def get_monthly_food_loss_reduction(db: Session, shop_id: str) -> float:
    """Get total value of food loss reduction this month."""
    now = get_current_time_utc()
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    query = select(func.coalesce(func.sum(col(Combo.original_price)), 0)).where(
        col(Combo.shop_id) == shop_id,
        col(Combo.status) == COMBO_STATUS_PICKED_UP,
        col(Combo.updated_at) >= month_start,
    )

    return db.exec(query).first() or 0.0


def get_pending_support_products_count(db: Session, shop_id: str) -> int:
    """Get count of products registered but not yet in locker."""
    query = select(func.count(col(Combo.id))).where(
        col(Combo.shop_id) == shop_id,
        col(Combo.status).in_([COMBO_STATUS_DRAFT, COMBO_STATUS_LOCKER_RESERVED]),
    )

    return db.exec(query).first() or 0


def get_month_to_date_revenue(db: Session, shop_id: str) -> float:
    """Get shop's revenue from the 1st of current month to now."""
    now = get_current_time_utc()
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    revenue_query = select(func.coalesce(func.sum(col(Order.final_price)), 0)).where(
        col(Order.shop_id) == shop_id,
        col(Order.status).in_(REVENUE_COUNTABLE_ORDER_STATUSES),
        col(Order.status) != ORDER_STATUS_REFUNDED,
        col(Order.completed_at) >= month_start,
        col(Order.completed_at) <= now,
    )
    result = db.exec(revenue_query).first()

    return float(result or 0.0)
