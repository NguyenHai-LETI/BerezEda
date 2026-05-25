"""
Redis distributed lock implementation for preventing race conditions
"""

import time
import uuid
from contextlib import contextmanager
from typing import Optional

from apps.core.logging import logger
from apps.integrations.redis.redis_client import get_redis_client


class RedisLock:
    """
    Distributed lock using Redis with automatic expiration
    """

    def __init__(
        self,
        key: str,
        timeout: int = 10,
        blocking: bool = True,
        blocking_timeout: Optional[int] = 5,
    ):
        """
        Initialize Redis lock

        Args:
            key: Lock key (e.g., 'combo:lock:{combo_id}')
            timeout: Lock expiration time in seconds (default: 10s)
            blocking: Whether to wait for lock acquisition (default: True)
            blocking_timeout: Max time to wait for lock in seconds (default: 5s)
        """
        self.key = f"lock:{key}"
        self.timeout = timeout
        self.blocking = blocking
        self.blocking_timeout = blocking_timeout
        self.identifier = str(uuid.uuid4())
        self.redis_client = get_redis_client()

    def acquire(self) -> bool:
        """
        Acquire the lock

        Returns:
            bool: True if lock acquired, False otherwise
        """
        end_time = time.time() + (self.blocking_timeout or 0)

        while True:
            # Try to set the lock with NX (only if not exists) and EX (expiration)
            acquired = self.redis_client.set(
                self.key, self.identifier, nx=True, ex=self.timeout
            )

            if acquired:
                logger.info(f"Lock acquired: {self.key} by {self.identifier}")
                return True

            if not self.blocking:
                logger.warning(f"Failed to acquire lock (non-blocking): {self.key}")
                return False

            # Check if we've exceeded blocking timeout
            if time.time() > end_time:
                logger.warning(
                    f"Failed to acquire lock after {self.blocking_timeout}s: {self.key}"
                )
                return False

            # Wait a bit before retrying
            time.sleep(0.1)

    def release(self) -> bool:
        """
        Release the lock (only if we own it)

        Returns:
            bool: True if lock released, False otherwise
        """
        # Lua script to ensure we only delete our own lock
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """

        try:
            result = self.redis_client.eval(lua_script, 1, self.key, self.identifier)
            if result:
                logger.info(f"Lock released: {self.key} by {self.identifier}")
                return True
            else:
                logger.warning(
                    f"Failed to release lock (not owner or expired): {self.key}"
                )
                return False
        except Exception as e:
            logger.error(f"Error releasing lock {self.key}: {e}")
            return False

    def __enter__(self):
        """Context manager entry"""
        if not self.acquire():
            from fastapi import HTTPException

            raise HTTPException(
                status_code=409,
                detail="この商品は現在処理中のため、しばらく時間をおいてから再度お試しください。",
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.release()


@contextmanager
def redis_lock(
    key: str,
    timeout: int = 10,
    blocking: bool = True,
    blocking_timeout: Optional[int] = 5,
):
    """
    Context manager for Redis distributed lock

    Usage:
        with redis_lock(f"combo:{combo_id}"):
            # Critical section
            pass

    Args:
        key: Lock key identifier
        timeout: Lock expiration time in seconds
        blocking: Whether to wait for lock acquisition
        blocking_timeout: Max time to wait for lock in seconds

    Raises:
        HTTPException: If lock cannot be acquired within timeout
    """
    lock = RedisLock(
        key=key,
        timeout=timeout,
        blocking=blocking,
        blocking_timeout=blocking_timeout,
    )

    try:
        if not lock.acquire():
            from fastapi import HTTPException

            raise HTTPException(
                status_code=409,
                detail="この商品は現在処理中のため、しばらく時間をおいてから再度お試しください。",
            )
        yield lock
    finally:
        lock.release()
