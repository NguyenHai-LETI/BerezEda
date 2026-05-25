from apps.integrations.redis.redis_client import get_redis_client


def check_rate_limit_service(key: str, limit: int, window: int, client=None) -> bool:
    redis_client = client or get_redis_client()

    current_count = redis_client.get(key)
    current_count = int(current_count) if current_count else 0

    if current_count == 0:
        # First hit in the window
        redis_client.setex(key, window, 1)
        return True

    if current_count < limit:
        # Still under limit; increment
        redis_client.incr(key)
        return True

    return False
