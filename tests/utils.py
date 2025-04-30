import asyncio
from typing import Any, Coroutine


def async_test(coro: Coroutine) -> Any:
    """Utility to run async tests in synchronous test runners"""

    def wrapper(*args, **kwargs):
        return asyncio.run(coro(*args, **kwargs))

    return wrapper


def cleanup_redis(redis_client, pattern: str = "*"):
    """Clean up test data from Redis"""
    keys = redis_client.keys(pattern)
    if keys:
        redis_client.delete(*keys)
