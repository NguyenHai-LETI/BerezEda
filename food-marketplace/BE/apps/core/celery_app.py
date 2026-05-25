import logging

logger = logging.getLogger(__name__)

try:
    from celery import Celery
    from celery.schedules import crontab
    _CELERY_AVAILABLE = True
except ImportError:
    _CELERY_AVAILABLE = False
    logger.warning("Celery not installed — background tasks will be no-ops.")

if _CELERY_AVAILABLE:
    # CRITICAL: Import all models to initialize SQLAlchemy relationships before Celery workers start
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

    celery_app.conf.beat_schedule = {
        "cleanup-revoked-tokens-every-30m": {
            "task": "auth.cleanup_revoked_tokens",
            "schedule": 3600,
            "args": (),
        },
        "cleanup-expired-combos": {
            "task": "apps.integrations.celery.systems.tasks.clean_expired_combos_and_lockers",
            "schedule": 200,
        },
        "clean_pickup_deadline_passed": {
            "task": "apps.integrations.celery.systems.tasks.clean_pickup_deadline_passed",
            "schedule": 200,
        },
        "reset-monthly-shop-stats": {
            "task": "apps.integrations.celery.shops.tasks.reset_monthly_shop_stats",
            "schedule": crontab(hour=15, minute=0),
        },
    }

else:
    class _NoOpTask:
        """No-op task stub for when Celery is not installed."""
        def __init__(self, fn):
            self._fn = fn
            self.__name__ = fn.__name__

        def __call__(self, *args, **kwargs):
            return self._fn(*args, **kwargs)

        def delay(self, *args, **kwargs):
            logger.debug(f"[no-op] Task {self.__name__} skipped (Celery not installed)")

        def apply_async(self, args=None, kwargs=None, countdown=None, eta=None, **opts):
            logger.debug(f"[no-op] Task {self.__name__} skipped (Celery not installed)")

    class _NoOpCelery:
        class conf:
            beat_schedule = {}

        def task(self, name=None, **kwargs):
            def decorator(fn):
                return _NoOpTask(fn)
            return decorator

    celery_app = _NoOpCelery()
