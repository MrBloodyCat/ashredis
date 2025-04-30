import functools
from typing import Callable, Coroutine
from redis.asyncio import Redis as AsyncRedis
from redis import Redis as SyncRedis


def with_async_redis_connection(func: Callable[..., Coroutine]) -> Callable[..., Coroutine]:
    """Decorator to manage Redis connection lifecycle for methods.

    Automatically creates a Redis connection if none exists when the method is called,
    and closes it after the method completes if the connection was created by this decorator.
    Args:
        func: The async function to be wrapped
    Returns:
        The wrapped function with connection management
    """

    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        is_wraps_connection = None
        if not self._redis:
            is_wraps_connection = True
            self._redis = await AsyncRedis(**self._redis_params.__dict__, decode_responses=True)
        try:
            result = await func(self, *args, **kwargs)
            return result
        finally:
            if is_wraps_connection is not None:
                await self._redis.aclose()
                self._redis = None

    return wrapper


def with_sync_redis_connection(func: Callable) -> Callable:
    """Decorator to manage Redis connection lifecycle for methods.

    Automatically creates a Redis connection if none exists when the method is called,
    and closes it after the method completes if the connection was created by this decorator.
    Args:
        func: The async function to be wrapped
    Returns:
        The wrapped function with connection management
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        is_wraps_connection = None
        if not self._redis:
            is_wraps_connection = True
            self._redis = SyncRedis(**self._redis_params.__dict__, decode_responses=True)
        try:
            result = func(self, *args, **kwargs)
            return result
        finally:
            if is_wraps_connection is not None:
                self._redis.close()
                self._redis = None

    return wrapper
