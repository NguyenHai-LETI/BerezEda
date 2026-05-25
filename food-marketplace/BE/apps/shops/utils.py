"""
Utility functions for shops module to reduce code duplication
"""

from typing import Optional, Sequence

from sqlmodel import Session

from apps.favorites import crud as favorite_crud
from apps.shops import schemas
from apps.shops.models.shops import Shop


def convert_single_shop_to_schema(
    shop: Shop, user_id: Optional[str], db: Session
) -> schemas.ShopRead:
    """Convert single Shop model to ShopRead schema with favorite status check."""
    is_favorite = False
    if user_id:
        favorite = favorite_crud.get_favorite_by_user_and_shop(db, user_id, shop.id)
        is_favorite = favorite is not None

    shop_data = schemas.ShopRead.model_validate(shop, from_attributes=True)
    shop_data.is_favorite = is_favorite
    return shop_data


def convert_multiple_shops_to_schema(
    shops: Sequence[Shop], user_id: str, db: Session
) -> list[schemas.ShopRead]:
    """Convert multiple Shop models to ShopRead schemas with batch favorite check."""
    if not shops:
        return []

    # Batch query for all favorites
    shop_ids = [shop.id for shop in shops]
    user_favorites = favorite_crud.get_favorites_by_user_and_shops(
        db, user_id, shop_ids
    )
    favorited_shop_ids = {fav.shop_id for fav in user_favorites}

    # Convert shops with pre-fetched favorite status
    result_shops = []
    for shop in shops:
        shop_data = schemas.ShopRead.model_validate(shop, from_attributes=True)
        shop_data.is_favorite = shop.id in favorited_shop_ids
        result_shops.append(shop_data)

    return result_shops


def generate_shop_code(db: Session):
    """
    Generate a unique random 6-digit shop code (numbers only).
    """
    import random

    while True:
        code = "".join(random.choices("0123456789", k=6))
        if not db.query(Shop).filter_by(code=code).first():
            return code
