ALLOWED_GLOBAL_UNAUTHENTICATED_PATHS = {
    "/health": "GET",
    "/docs": "GET",
    "/openapi.json": "GET",
    "/mynumber": "GET",
}

ALLOWED_UNAUTHENTICATED_PATHS = {
    "/users/": "POST",
    "/auth/token": "POST",
    "/auth/refresh-token": "POST",
    "/users/forgot-password": "POST",
    "/users/reset-password": "POST",
    "/users/verify-code": "POST",
    "/users/myna_go_jp": "POST",
    "/external/prefectures": "GET",
    "/external/municipalities": "GET",
    "/purchase-callbacks/webhook/card-registration": "POST",
    "/purchase-callbacks/webhook/payment-execute": "POST",
    "/purchase-callbacks/webhook/3d-secure": "POST",
    "/combos/public": "GET",
    "/lockers/locations/public": "GET",
    "/lockers/locations/*": "GET",  # Allows GET /api/lockers/locations/{location_id}
    "/combos/location/*": "GET",
    "/combos/*": "GET",  # Allows GET /api/combos/{combo_id}
    "/shops/location/*": "GET",  # Allows GET /api/shops/location/{location_id}
    "/shops/*": "GET",  # Allows GET /api/shops/{shop_id}
    "/shops/*/combos": "GET",  # Allows GET /api/shops/{shop_id}/combos
    "/devices/": "POST",
    "/notifications/": "GET",
    "/notifications/public/*": "GET",
}

# Specific paths that should NOT match the wildcard pattern above
# These require authentication even though they match the wildcard pattern
EXCLUDED_FROM_WILDCARD_PATTERNS = {
    "/combos/": ["GET"],  # GET /v1/combos/ requires auth (list combos)
    "/shops/": ["GET"],  # GET /v1/shops/ requires auth (list shops)
    "/shops/my-shop": ["GET"],  # GET /v1/shops/my-shop requires auth (get my shop)
}

# Timing Constants (configurable via environment variables)
# NOTE:
# - These are defined in `apps/core/config.py` (loaded from `.env` via python-dotenv).
# - They are re-exported here because many modules import them from `apps.core.constants`.
from apps.core.config import (  # noqa: E402
    COMBO_PREPARATION_TIME_MINUTES,
    MIN_FREE_PURCHASE_INTERVAL,
    PICK_UP_DEADLINE,
    SHOP_COOLDOWN_MINUTES,
)

DOMAIN = "https://api.wakeatte.net"

# Combo Status Constants
# DRAFT -> PREPARATION_TO_LOCKER -> SELLING -> SOLD
#                                |-> EXPIRED (listing timeout, no buyer)
#                    |-> EXPIRED_PUT_IN_LOCKER (staff didn't put item in locker in time)
# Any status -> DELETED (shop cancels combo, soft-delete)
COMBO_STATUS_DRAFT = "DRAFT"
COMBO_STATUS_PREPARATION_TO_LOCKER = "PREPARATION_TO_LOCKER"
COMBO_STATUS_EXPIRED_PUT_IN_LOCKER = "EXPIRED_PUT_IN_LOCKER"
COMBO_STATUS_SELLING = "SELLING"
COMBO_STATUS_SOLD = "SOLD"
COMBO_STATUS_EXPIRED = "EXPIRED"
COMBO_STATUS_DELETED = "DELETED"

# Order Status Constants
# PENDING_PAYMENT -> READY_FOR_PICKUP -> PICKED_UP
# Legacy statuses (no longer set, may exist in old DB records): EXPIRED, CANCELLED
ORDER_STATUS_PENDING_PAYMENT = "PENDING_PAYMENT"  # Payment initiated, waiting for result
ORDER_STATUS_READY_FOR_PICKUP = "READY_FOR_PICKUP"  # Payment successful, user can pick up item
ORDER_STATUS_PICKED_UP = "PICKED_UP"  # User picked up item or pickup deadline passed
ORDER_STATUS_REFUNDED = "REFUNDED"

# Payment Status Constants
PAYMENT_INIT = "INIT"
PAYMENT_UNPROCESSED = "UNPROCESSED"
PAYMENT_CAPTURED = "CAPTURED"
PAYMENT_FAILED = "FAILED"


# Payment order status
PAYMENT_STATUS_PENDING = "PENDING"
PAYMENT_STATUS_COMPLETED = "COMPLETED"
PAYMENT_STATUS_FAILED = "FAILED"
PAYMENT_STATUS_REFUNDED = "REFUNDED"

# Favorite Lockers (My Locker) - max per user
MAX_FAVORITE_LOCKERS = 3
MAX_SEARCH_HISTORY_LOCKERS = 5
MAX_LOCKER_COLUMN = 10
MAX_ACCESS_CODE_RETRIES = 5

# Locker Unit Status
UNIT_STATUS_AVAILABLE = "AVAILABLE"
UNIT_STATUS_RESERVED = "RESERVED"
UNIT_STATUS_OCCUPIED = "OCCUPIED"
UNIT_STATUS_MAINTENANCE = "MAINTENANCE"

# Reservation Status
RESERVATION_STATUS_PENDING = "PENDING"
RESERVATION_STATUS_ACTIVE = "ACTIVE"
RESERVATION_STATUS_COMPLETED = "COMPLETED"
RESERVATION_STATUS_CANCELLED = "CANCELLED"

# Time-based thresholds
PRICE_REDUCTION_THRESHOLD = 1 / 3
LOCKER_PLACEMENT_TIMEOUT = (
    20 * 60
)  # 20 minutes in seconds (matches COMBO_PREPARATION_TIME_MINUTES)

COMBO_DELETABLE_STATUSES = [
    COMBO_STATUS_DRAFT,
    COMBO_STATUS_EXPIRED,
    COMBO_STATUS_DELETED,
]

COMBO_UPDATABLE_STATUSES = [COMBO_STATUS_DRAFT, COMBO_STATUS_SELLING]

COMBO_SALE_HISTORY_STATUSES = [
    COMBO_STATUS_PREPARATION_TO_LOCKER,
    COMBO_STATUS_EXPIRED_PUT_IN_LOCKER,
    COMBO_STATUS_SELLING,
    COMBO_STATUS_SOLD,
    COMBO_STATUS_EXPIRED,
]

# Payment Methods
PAYMENT_METHOD_CARD = "card"
PAYMENT_METHOD_DIGITAL = "digital"
PAYMENT_METHOD_FREE = "free"

# Locker Unit Sizes
UNIT_SIZE_SMALL = "small"
UNIT_SIZE_MEDIUM = "medium"
UNIT_SIZE_LARGE = "large"
UNIT_SIZE_EXTRA_LARGE = "extra_large"

UNIT_SIZE_CHOICES = [
    UNIT_SIZE_SMALL,
    UNIT_SIZE_MEDIUM,
    UNIT_SIZE_LARGE,
    UNIT_SIZE_EXTRA_LARGE,
]

# Locker Unit Status Choices
UNIT_STATUS_CHOICES = [
    UNIT_STATUS_AVAILABLE,
    UNIT_STATUS_RESERVED,
    UNIT_STATUS_OCCUPIED,
    UNIT_STATUS_MAINTENANCE,
]

# Timing Constants (in minutes)
# The following are imported from config.py for environment configurability:
# - COMBO_PREPARATION_TIME_MINUTES
# - SHOP_COOLDOWN_MINUTES
# - PICK_UP_DEADLINE
# - MIN_FREE_PURCHASE_INTERVAL
COMBO_SALE_TIME_HOURS = 8
COMBO_PRICE_REDUCTION_THRESHOLD = 0.33

# Order statuses that count towards revenue / statistics.
# Refunded orders must be excluded from all revenue and sales calculations.
REVENUE_COUNTABLE_ORDER_STATUSES = [
    ORDER_STATUS_PICKED_UP,
    ORDER_STATUS_READY_FOR_PICKUP,
]

# Revenue Percentage
LOCKER_OWNER_REVENUE_PERCENTAGE = 0.25
ADMIN_REVENUE_PERCENTAGE = 1.0

# Additional Constants
COMBO_PURCHASABLE_STATUSES = [
    COMBO_STATUS_SELLING,
]

COMBO_NOT_IN_LOCKER_LOCATION_STATUSES = [
    COMBO_STATUS_EXPIRED,
    COMBO_STATUS_DRAFT,
    COMBO_STATUS_DELETED,
    COMBO_STATUS_PREPARATION_TO_LOCKER,
    COMBO_STATUS_EXPIRED_PUT_IN_LOCKER,
]
