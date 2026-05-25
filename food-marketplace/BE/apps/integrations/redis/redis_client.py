import redis

from apps.core.config import REDIS_URL
from apps.core.logging import logger

# Global Redis client instance
_redis_client = None


def get_redis_client() -> redis.Redis:
    """Get Redis client instance with connection pooling"""
    global _redis_client

    try:
        if _redis_client is None:
            _redis_client = redis.Redis.from_url(
                REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
            )
            # Test the connection
            _redis_client.ping()

        return _redis_client
    except Exception as e:
        logger.error(f"Redis connection failed: {str(e)}")
        from apps.users.exceptions import redis_unavailable

        raise redis_unavailable()
