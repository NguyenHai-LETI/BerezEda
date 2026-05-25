# Import all models so SQLModel.metadata.create_all() picks them up

from apps.users.models.users import User
from apps.auth.models.revoked_token import RevokedToken
from apps.shops.models.shops import Shop
from apps.lockers.models.shop_locker_association import ShopLockerAssociation
from apps.lockers.models.shop_cooldown import ShopCooldown
from apps.products.models.product import ProductMaster
from apps.lockers.models.location import LockerLocation
from apps.lockers.models.unit import LockerUnit
from apps.lockers.models.favorite_locker import FavoriteLocker
from apps.lockers.models.reservation import LockerReservation
from apps.combos.models.combo import Combo, ComboProduct
from apps.orders.models.order import Order
from apps.payments.models.payment import Payment, Card, FincodeUser
from apps.devices.models.device import Device
from apps.notifications.models.notification import Notification
from apps.reviews.models.review import Review
from apps.favorites.models.favorite import Favorite

__all__ = [
    "User", "RevokedToken",
    "Shop", "ShopLockerAssociation", "ShopCooldown",
    "ProductMaster",
    "LockerLocation", "LockerUnit", "FavoriteLocker", "LockerReservation",
    "Combo", "ComboProduct",
    "Order",
    "Payment", "Card", "FincodeUser",
    "Device",
    "Notification",
    "Review",
    "Favorite",
]
