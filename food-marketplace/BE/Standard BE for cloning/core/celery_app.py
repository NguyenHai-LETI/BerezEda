from celery import Celery
from celery.schedules import crontab

# CRITICAL: Import all models to initialize SQLAlchemy relationships before Celery workers start
# This prevents mapper initialization errors in Celery tasks
from apps.core import models  # noqa: F401
from apps.core.config import REDIS_URL

celery_app = Celery(
    "wakeatte",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "apps.auth.tasks",
        "apps.users.tasks",
        "apps.shops.tasks",
        "apps.orders.tasks",
        "apps.lockers.tasks",
        "apps.products.tasks",
        "apps.integrations.celery.systems.tasks",
        "apps.integrations.celery.users.tasks",
        "apps.integrations.celery.shops.tasks",
    ],
)

# Beat schedule: scheduled tasks for monitoring and notifications
celery_app.conf.beat_schedule = {
    "cleanup-revoked-tokens-every-30m": {
        "task": "auth.cleanup_revoked_tokens",
        "schedule": 3600,
        "args": (),
    },
    # clean combos and locker when sales expired and not sold
    "cleanup-expired-combos": {
        "task": "apps.integrations.celery.systems.tasks.clean_expired_combos_and_lockers",
        "schedule": 200,
    },
    # send noti when pickup deadline passed without collection and change status of order and locker
    "clean_pickup_deadline_passed": {
        "task": "apps.integrations.celery.systems.tasks.clean_pickup_deadline_passed",
        "schedule": 200,
    },
    # DEPRECATED: Replaced by PRODUCT_EXPIRY_REACHED (trigger-based via apply_async eta)
    # "check-product-expired-date": {
    #     "task": "apps.integrations.celery.systems.tasks.check_product_expired_date",
    #     "schedule": 200,
    # },
    # reset monthly shop stats at 00:00 JST on the 1st of each month
    # Schedule to run at 15:00 UTC daily, task will check if it's 00:00 JST on the 1st
    "reset-monthly-shop-stats": {
        "task": "apps.integrations.celery.shops.tasks.reset_monthly_shop_stats",
        "schedule": crontab(hour=15, minute=0),
    },
}
