"""
Model registry to ensure proper SQLModel relationship resolution.
This file imports all models in the correct order to avoid circular import issues.
"""

from apps.auth.models import *  # noqa

# Configure relationships after all models are imported
from apps.core.relationship_config import configure_model_relationships
from apps.devices.models import *  # noqa
from apps.favorites.models import *  # noqa
from apps.favorites.models.favorites import Favorite  # noqa
from apps.lockers.models import *  # noqa
from apps.lockers.models.favorite_locker import FavoriteLocker  # noqa
from apps.mynaportal.models import *  # noqa
from apps.mynaportal.models.myna_authorizer import MynaAuthorizer  # noqa
from apps.mynaportal.models.user_welfare_support import UserWelfareSupport  # noqa
from apps.notifications.models import *  # noqa
from apps.orders.models import *  # noqa
from apps.products.models import *  # noqa
from apps.purchase.models import *  # noqa
from apps.qrcode.models.qrcode import *  # noqa
from apps.reviews.models import *  # noqa

# Import models in dependency order to ensure they're available for relationship resolution
# Base models first (no dependencies)
from apps.shops.models import *  # noqa - Shops first as base model
from apps.shops.models.shops import Shop  # noqa

# Models that depend on base models
from apps.users.models import *  # noqa - Users after shops are defined

# Try to configure relationships
_relationships_configured = configure_model_relationships()

# This ensures all relationships can be resolved
__all__ = [
    "Device",
    "Favorite",
    "FavoriteLocker",
    "Shop",
    "MynaAuthorizer",
    "UserWelfareSupport",
    "UserFincode",
    "Payment",
]
