from sqlmodel import Session

from apps.core.constants import COMBO_STATUS_SELLING
from apps.core.schemas import DEFAULT_LIMIT, DEFAULT_OFFSET
from apps.core.utils import get_distance
from apps.favorites import crud
from apps.favorites.exceptions import favorite_already_exists, favorite_not_found
from apps.products.models.combos import Combo
from apps.shops import schemas
from apps.shops.crud import get_shop
from apps.shops.exceptions import shop_not_found
from apps.users.models.users import User


def get_liked_shop_service(
    db: Session,
    user: User,
    limit: int = DEFAULT_LIMIT,
    offset: int = DEFAULT_OFFSET,
    user_location: str | None = None,
):
    """
    Get liked shops for a user with pagination using user.favorites relationship.

    Args:
        db: Database session
        user: Authenticated user object (from get_authenticated_user_with_db)
        limit: Maximum number of items to return
        offset: Number of items to skip

    Returns:
        Tuple of (shop_list, total_count)
    """
    all_favorites = user.favorites
    all_favorites.sort(key=lambda x: x.favorited_at, reverse=True)

    favorite_of_active_shop = [
        favorite
        for favorite in all_favorites
        if (favorite.shop and favorite.shop.is_active)
    ]
    total = len(favorite_of_active_shop)
    paginated_favorites = favorite_of_active_shop[offset : offset + limit]

    # Convert shops to ShopRead schema with is_favorite=True (since these are from favorites)
    # Avoid N+1 query by directly setting is_favorite=True instead of calling _convert_shop_to_schema
    shops = []
    for favorite in paginated_favorites:
        shop_schema = schemas.ShopReadWithDistance.model_validate(
            favorite.shop, from_attributes=True
        )
        shop_schema.is_favorite = True
        # compute distance if coords provided and shop has position
        if not "None" in user_location and favorite.shop and favorite.shop.position:
            shop_schema.distance = get_distance(user_location, favorite.shop.position)
        else:
            shop_schema.distance = None

        number_combos = (
            db.query(Combo)
            .filter(
                Combo.shop_id == favorite.shop.id, Combo.status == COMBO_STATUS_SELLING
            )
            .count()
        )
        shop_schema.number_combos = int(number_combos)
        shops.append(shop_schema)

    return shops, total


def like_or_dislike_service(db: Session, user: User, is_like: bool, shop_id: str):
    """
    Handle like/dislike functionality for shops.

    Args:
        db: Database session
        user: Authenticated user object (from get_authenticated_user_with_db)
        is_like: True for like, False for dislike
        shop_id: Shop ID to like/dislike (as string)

    Returns:
        Dictionary with action performed
    """
    user_id = user.id

    # dislike
    if not is_like:
        fav = crud.get_favorite_by_user_and_shop(db, user_id, shop_id)
        if fav:
            crud.delete_favorite(db, fav)
            return {"action": "removed"}
        raise favorite_not_found()

    # like
    # Validate shop exists before creating favorite
    shop = get_shop(db, shop_id)
    if not shop:
        raise shop_not_found()

    existing = crud.get_favorite_by_user_and_shop(db, user_id, shop_id)
    if existing:
        raise favorite_already_exists()
    crud.create_favorite(db, user_id, shop_id)
    return {"action": "added"}
