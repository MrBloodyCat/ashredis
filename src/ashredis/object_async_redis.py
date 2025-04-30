from __future__ import annotations

import asyncio
import json
from copy import deepcopy
from datetime import timedelta
from time import time
from typing import Any, Type

from redis.asyncio import Redis

from .decorators import with_async_redis_connection
from .enums import StreamEvent, DefaultKeys
from .models import RedisParams


class AsyncRedisObject:
    """Base class for Redis-backed objects with typed fields and automatic serialization."""
    __category__ = None
    __default_key__ = None

    def __init__(self, redis_params: RedisParams = None, key: str | int = None, path: list[str] = None):
        """Initialize a RedisObject instance.
        Args:
            redis_params: Redis server params
            key: Optional key for this object in Redis
            path: Optional path segments for hierarchical keys
        """
        self.key = key
        self.path = path
        self._path_str = f":{":".join(path)}:" if path else ":"
        self._redis_params = redis_params
        self._redis = None
        self._data = {}
        self._fields = {}

        self.__parse_fields()
        self.__parse_configure()

    async def __aenter__(self):
        """Async context manager entry point."""
        self._redis = await Redis(**self._redis_params.__dict__, decode_responses=True).__aenter__()
        return self

    async def __aexit__(self, *args):
        """Async context manager exit point."""
        await self._redis.__aexit__(*args)

    @classmethod
    def __typed_property(cls, key_name: str, data_type: Type):
        """Create a typed property for Redis field with automatic serialization.
        Args:
            key_name: Name of the field/property
            data_type: Python type for this field
        Returns:
            A property object with getter and setter that handles type conversion
        """

        def getter(self) -> Any:
            data = self._data.get(key_name)
            if data is None:
                return None
            elif data_type == bool:
                return bool(data)
            elif data_type in (dict, list):
                return json.loads(data)
            return data

        def setter(self, value: Any):
            if value is None:
                self._data[key_name] = None
            elif data_type == bool:
                self._data[key_name] = int(value)
            elif data_type in (dict, list):
                self._data[key_name] = json.dumps(value)
            elif isinstance(value, data_type):
                self._data[key_name] = value
            else:
                raise TypeError(
                    f"Field '{key_name}' expected type {data_type.__name__}, "
                    f"but got value '{value}' of type {type(value).__name__}."
                )

        return property(getter, setter)

    def __parse_fields(self):
        """Parse class annotations to create typed properties."""
        if not hasattr(self, "__annotations__"):
            return

        for field_name, field_type in self.__annotations__.items():
            self._fields[field_name] = field_type
            setattr(self.__class__, field_name, self.__typed_property(field_name, field_type))

    def __parse_configure(self):
        """Validate configuration and set default key if needed."""
        if not hasattr(self, '__category__'):
            raise AttributeError(f"{self.__class__.__name__} must define '__category__' attribute.")

        if self.key is None:
            self.key = getattr(self, '__default_key__', None)

    def __converted_data(self, key: str, value: str):
        """Convert Redis string values to appropriate Python types.
        Args:
            key: Field name
            value: String value from Redis
        """
        type_mapping = {
            int: int,
            float: float,
            list: json.loads,
            dict: json.loads,
            bool: lambda x: bool(int(x)),
        }

        value_type = self._fields.get(key)
        if not value_type:
            return

        value = type_mapping.get(value_type, lambda x: x)(value)
        setattr(self, key, value)

    async def __get_all_keys(self, offset: int = None, limit: int = None) -> list:
        """Get all Redis keys matching this object's category pattern.
        Args:
            offset: Optional offset for pagination
            limit: Optional limit for pagination
        Returns:
            List of matching keys
        """
        count = limit if limit and not offset else None
        all_keys = []
        cursor = 0
        while True:
            cursor, keys = await self._redis.scan(cursor, match=f"{self.__category__}{self._path_str}*", count=count)
            all_keys.extend(keys)
            if cursor == 0:
                break

        return all_keys[offset:][:limit]

    async def __get_items_from_dict(self, data: dict):
        """Create a RedisObject instance from stream event data.
        Args:
            data: Dictionary containing 'hash_key' and field values
        Returns:
            A populated RedisObject instance
        """
        hash_key = data.get("hash_key")
        if not hash_key:
            return

        result = await self._redis.hgetall(name=hash_key)
        path_keys = hash_key.split(":")
        key = path_keys[-1]
        key = int(key) if key.isdigit() else key
        path = [i for i in path_keys[1:-1]] if len(path_keys) >= 3 else None

        item = type(self)(key=key, path=path)
        for k, v in result.items():
            item.__converted_data(key=k, value=v)

        return item

    def __create_objects_from_results(self, keys: list, results: list, sort_field: str = None,
                                      ts_by_range: int = None) -> list:
        """Helper to create objects from keys and pipeline results."""
        items = []
        for key, result in zip(keys, results):
            path_keys = key.split(":")
            key = path_keys[-1]
            key = int(key) if key.isdigit() else key
            path = [i for i in path_keys[1:-1]] if len(path_keys) >= 3 else None

            item = type(self)(key=key, path=path)
            for k, v in result.items():
                item.__converted_data(key=k, value=v)

            if sort_field is None:
                items.append(item)
                continue

            if ts_by_range is None:
                if sort_field in item._data:
                    items.append(item)
                continue

            ts = item._data.get(sort_field)
            if ts and ts > ts_by_range:
                items.append(item)

        return items

    def get_dict(self) -> dict:
        """Get the internal data dictionary."""
        return {k: json.loads(v) if self._fields[k] in (dict, list) else v for k, v in self._data.items()}

    def load_dict(self, data: dict):
        """Load data from a dictionary."""
        if not isinstance(data, dict):
            raise TypeError("Data must be a dictionary")
        for key, value in data.items():
            value = json.dumps(value) if type(value) in (dict, list) else value
            self.__converted_data(key=key, value=value)

    def copy(self, category: AsyncRedisObject):
        """Copy data from another category."""
        if not isinstance(category, AsyncRedisObject):
            raise TypeError("Category must be a RedisObject instance")
        self._data = deepcopy(category._data)

    @with_async_redis_connection
    async def load(self, key: str | int = None) -> bool:
        """Load object data from Redis.
        Args:
            key: Optional key to load (uses instance key if None)
        Returns:
            True if data was loaded successfully, False otherwise
        """
        self.key = key or self.key
        if self.key is None:
            raise ValueError("key does not exist")

        if self._data:
            self._data = {}

        result = await self._redis.hgetall(name=f"{self.__category__}{self._path_str}{self.key}")
        for key, value in result.items():
            self.__converted_data(key=key, value=value)

        return True if self._data else False

    @with_async_redis_connection
    async def load_all(self, offset: int = None, limit: int = None) -> list:
        """Load all objects of this type from Redis.
        Args:
            offset: Optional offset for pagination
            limit: Optional limit for pagination
        Returns:
            List of RedisObject instances
        """
        all_keys = await self.__get_all_keys(offset=offset, limit=limit)

        pipeline = self._redis.pipeline()
        for key in all_keys:
            pipeline.hgetall(key)
        results = await pipeline.execute()

        return self.__create_objects_from_results(all_keys, results)

    @with_async_redis_connection
    async def load_for_time(self, ts_field: str, time_range: timedelta = None, offset: int = None, limit: int = None,
                            sort: bool = False, reverse_sorted: bool = False) -> list:
        """Load objects within a time range based on a timestamp field.
        Args:
            ts_field: Name of the timestamp field to filter by
            time_range: Time range to look back from now
            offset: Optional offset for pagination
            limit: Optional limit for pagination
            sort: True to sort the records
            reverse_sorted: Whether to sort in reverse order
        Returns:
            List of RedisObject instances within the time range
        """
        if time_range is None:
            time_range = timedelta()

        ts_by_range = int(time() * 1000) - int(time_range.total_seconds() * 1000)
        all_keys = await self.__get_all_keys()

        pipeline = self._redis.pipeline()
        for key in all_keys:
            pipeline.hgetall(key)
        results = await pipeline.execute()

        categories = self.__create_objects_from_results(keys=all_keys, results=results, sort_field=ts_field,
                                                        ts_by_range=ts_by_range)
        if sort:
            categories = sorted(categories, key=lambda i: i._data[ts_field], reverse=not reverse_sorted)
        return categories[offset:][:limit]

    @with_async_redis_connection
    async def load_sorted(self, sort_field: str, reverse_sorted: bool = False, offset: int = None,
                          limit: int = None) -> list:
        """Load all objects sorted by a specific field.
        Args:
            sort_field: Field name to sort by
            reverse_sorted: Whether to sort in reverse order
            offset: Optional offset for pagination
            limit: Optional limit for pagination
        Returns:
            List of RedisObject instances sorted by the specified field
        """
        all_keys = await self.__get_all_keys()

        pipeline = self._redis.pipeline()
        for key in all_keys:
            pipeline.hgetall(key)
        results = await pipeline.execute()

        categories = self.__create_objects_from_results(keys=all_keys, results=results, sort_field=sort_field)

        sorted_categories = sorted(categories, key=lambda i: i._data[sort_field], reverse=not reverse_sorted)
        return sorted_categories[offset:][:limit]

    @with_async_redis_connection
    async def save(self, key: str | int = None, stream: bool = False, ttl: timedelta = None):
        """Save object data to Redis.
        Args:
            key: Optional key to save under (uses instance key if None)
            stream: Whether to publish a stream event about the save
            ttl: Optional time-to-live for the Redis key
        """
        self.key = key or self.key
        if self.key is None:
            raise ValueError("key does not exist")

        if not self._data:
            return

        hash_key = f"{self.__category__}{self._path_str}{self.key}"
        pipeline = self._redis.pipeline()

        data_to_store = {k: v for k, v in self._data.items() if v is not None}
        fields_to_remove = [k for k, v in self._data.items() if v is None]

        if data_to_store:
            pipeline.hset(hash_key, mapping=data_to_store)
        if fields_to_remove:
            pipeline.hdel(hash_key, *fields_to_remove)

        if ttl:
            pipeline.expire(hash_key, int(ttl.total_seconds()))

        if stream:
            pipeline.xadd(
                f"{self.__category__}{self._path_str}{DefaultKeys.STREAM_KEY.value}",
                {"event": StreamEvent.SAVE.value, "hash_key": hash_key}
            )

        await pipeline.execute()

    @with_async_redis_connection
    async def delete(self, key: str | int = None) -> bool:
        """Delete object data from Redis.
        Args:
            key: Optional key to delete (uses instance key if None)
        Returns:
            True if deletion was successful, False otherwise
        """
        self.key = key or self.key
        if self.key is None:
            raise ValueError("key does not exist")

        result = await self._redis.delete(f"{self.__category__}{self._path_str}{self.key}")
        return True if result else False

    @with_async_redis_connection
    async def get_ttl(self, key: str | int = None) -> int | None:
        """Get time-to-live for object's Redis key.
        Args:
            key: Optional key to check (uses instance key if None)
        Returns:
            TTL in seconds, or None if key doesn't exist or has no TTL
        """
        self.key = key or self.key
        if self.key is None:
            raise ValueError("key does not exist")

        ttl = await self._redis.ttl(f"{self.__category__}{self._path_str}{self.key}")
        if ttl != -2:
            return ttl

    @with_async_redis_connection
    async def get_stream_in_interval(self, start_ts: int, end_ts: int) -> list:
        """Get stream events within a timestamp range.
        Args:
            start_ts: Start timestamp (milliseconds)
            end_ts: End timestamp (milliseconds)
        Returns:
            List of RedisObject instances created from stream events
        """
        stream_key = f"{self.__category__}{self._path_str}{DefaultKeys.STREAM_KEY.value}"

        start_id = f"{start_ts}-0"
        end_id = f"{end_ts}-9999999"
        events = await self._redis.xrange(stream_key, start_id, end_id)
        items = []

        for event_id, event_data in events:
            item = await self.__get_items_from_dict(data=event_data)
            items.append(item)

        return items

    @with_async_redis_connection
    async def listen_for_stream(self, callback, delay: int = 1):
        """Continuously listen for new stream events and invoke callback.
        Args:
            callback: Async function to call with each new event
            delay: Delay between checks in seconds
        """
        stream_key = f"{self.__category__}{self._path_str}{DefaultKeys.STREAM_KEY.value}"
        last_id = "$"

        while True:
            events = await self._redis.xread({stream_key: last_id}, block=0, count=1)
            if not events:
                continue

            for event in events[0][1]:
                last_id = event[0]
                event_data = event[1]

                item = await self.__get_items_from_dict(data=event_data)
                await callback(item)

            await asyncio.sleep(delay)
