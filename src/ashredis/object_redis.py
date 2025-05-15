import json
from dataclasses import is_dataclass
from datetime import timedelta
from typing import TypeVar, Type, Union, List, get_type_hints, get_origin, get_args

from redis.asyncio import Redis

from .enums import StreamEvent, DefaultKeys
from .models import RedisParams
from .record_base import RecordBase

T = TypeVar("T", bound=RecordBase)
DEFAULT_SCAN_COUNT = 10000


class RedisManager:
    def __init__(self, redis_params: RedisParams):
        """
        Initializes a new instance of RedisObject.

        Args:
            redis_params (RedisParams): Parameters for Redis connection.
        """
        self._redis_params = redis_params
        self._redis = None

    async def __aenter__(self):
        """
        Async context manager entry point. Establishes connection to Redis.

        Returns:
            RedisManager: The instance with an active Redis connection.
        """
        self._redis = await Redis(**self._redis_params.__dict__, decode_responses=True).__aenter__()
        return self

    async def __aexit__(self, *args):
        """
        Async context manager exit point. Closes the Redis connection.

        Args:
            *args: Exception details if an exception occurred.
        """
        await self._redis.__aexit__(*args)

    @staticmethod
    def __collect_hash_key(category: str, key: str | int | list[str | int]):
        if isinstance(key, list):
            key = ":".join([_ if isinstance(_, str) else str(_) for _ in key])
        return f"{category}:{key}"

    @staticmethod
    def __collect_list_keys(hash_key: str):
        return hash_key.split(":")[1:]

    @staticmethod
    def __prepare_record_data(record: T):
        data_to_store = {}
        fields_to_remove = []
        record_hash = record.to_hash()
        for k, v in record_hash.items():
            if record.loaded_hash and k in record.loaded_hash and v == record.loaded_hash[k]:
                continue
            elif v is None:
                fields_to_remove.append(k)
            else:
                data_to_store[k] = v
        return data_to_store, fields_to_remove

    @staticmethod
    def __add_record_to_pipeline(pipeline, hash_key: str, data_to_store: dict, fields_to_remove: list,
                                 ttl: timedelta = None, record: T = None, stream_key: str = None):
        if data_to_store:
            pipeline.hset(hash_key, mapping=data_to_store)
        if fields_to_remove:
            pipeline.hdel(hash_key, *fields_to_remove)

        if ttl:
            pipeline.expire(hash_key, int(ttl.total_seconds()))

        if stream_key and record and (data_to_store or fields_to_remove):
            event = StreamEvent.UPDATE.value if record.loaded_hash else StreamEvent.SAVE.value
            pipeline.xadd(
                f"{record.category()}:{stream_key}:{DefaultKeys.STREAM_KEY.value}",
                {"event": event, "hash_key": hash_key}
            )

    def __parse_to_dataclass(self, record_type: Type[T], data: dict, inclusion=False) -> T:
        hints = get_type_hints(record_type)
        kwargs = {}

        for field, field_type in hints.items():
            if field not in data:
                continue

            value = data[field]

            if get_origin(field_type) is Union:
                field_type = get_args(field_type)[0]

            if isinstance(value, str) and not field_type is str:
                value = json.loads(value)

            if is_dataclass(field_type) and isinstance(value, dict):
                kwargs[field] = self.__parse_to_dataclass(field_type, value, True)
            elif field_type is int and value is not None:
                kwargs[field] = int(value)
            elif field_type is float and value is not None:
                kwargs[field] = float(value)
            elif field_type is bool and value is not None:
                kwargs[field] = bool(int(value)) if isinstance(value, str) else bool(value)
            else:
                kwargs[field] = value
        record = record_type(**kwargs)
        if not inclusion:
            record.loaded_hash = record.to_hash()
        return record

    async def __process_loaded_records(self, record_type: Type[T], hash_keys: list, results: list) -> list[T]:
        records = []
        for result, key in zip(results, hash_keys):
            record = self.__parse_to_dataclass(record_type=record_type, data=result)
            record.key = self.__collect_list_keys(key)
            records.append(record)
        return records

    async def __scan_hash_keys(self, hash_key: str, limit: int = None, offset: int = None,
                               scan_count: int = DEFAULT_SCAN_COUNT) -> list:
        cursor = 0
        hash_keys = []
        if limit:
            scan_count = sum((limit, offset or 0))

        while True:
            cursor, keys = await self._redis.scan(cursor, match=hash_key, count=scan_count)
            hash_keys.extend(keys)
            if not cursor or (limit and len(hash_keys) >= scan_count):
                break

        if not hash_keys:
            return []

        if offset or limit:
            hash_keys = hash_keys[offset:][:limit]

        return hash_keys

    async def save(self, record: T, key: str | int | list[str | int], ttl: timedelta = None, stream_key: str = None):
        """
        Saves a record to Redis.

        Args:
            record (T): The record to save, must be a subclass of RecordBase.
            key (str | int | list[str | int]): The key or key components to identify the record.
            ttl (timedelta, optional): Time-to-live for the record. If None, the record won't expire.
            stream_key (str, optional): If provided, adds an entry to a Redis stream for this operation.
        """
        hash_key = self.__collect_hash_key(category=record.category(), key=key)
        pipeline = self._redis.pipeline()

        data_to_store, fields_to_remove = self.__prepare_record_data(record)
        self.__add_record_to_pipeline(pipeline, hash_key, data_to_store, fields_to_remove, ttl, record, stream_key)

        await pipeline.execute()

    async def save_many(self, records: List[T], keys: List[str | int | list[str | int]], ttl: timedelta = None,
                        stream_key: str = None):
        """
        Saves multiple records to Redis in a single pipeline.
        
        Args:
            records (List[T]): List of records to save, must be subclasses of RecordBase.
            keys (List[str | int | list[str | int]]): List of keys corresponding to each record.
            ttl (timedelta, optional): Time-to-live for all records. If None, the records won't expire.
            stream_key (str, optional): If provided, adds entries to a Redis stream for these operations.
            
        Raises:
            ValueError: If the number of records doesn't match the number of keys.
        """
        if len(records) != len(keys):
            raise ValueError("The number of records must correspond to the number of keys")

        pipeline = self._redis.pipeline()

        for record, key in zip(records, keys):
            hash_key = self.__collect_hash_key(category=record.category(), key=key)
            data_to_store, fields_to_remove = self.__prepare_record_data(record)
            self.__add_record_to_pipeline(pipeline, hash_key, data_to_store, fields_to_remove, ttl, record, stream_key)

        await pipeline.execute()

    async def load(self, record_type: Type[T], key: str | int | list[str | int]) -> T | None:
        """
        Loads a record from Redis.
        
        Args:
            record_type (Type[T]): The type of record to load, must be a subclass of RecordBase.
            key (str | int | list[str | int]): The key or key components that identify the record.
            
        Returns:
            T: An instance of the specified record type with data from Redis.
            If the record doesn't exist, return None.
        """
        hash_key = self.__collect_hash_key(category=record_type.category(), key=key)
        result = await self._redis.hgetall(name=hash_key)
        if not result:
            return None

        record = self.__parse_to_dataclass(record_type=record_type, data=result)
        record.key = self.__collect_list_keys(hash_key)
        return record

    async def load_many(self, record_type: Type[T], key: str | int | list[str | int], limit: int = None,
                        offset: int = None, scan_count: int = DEFAULT_SCAN_COUNT) -> list[T]:
        """
        Loads multiple records from Redis that match a pattern.
        
        Args:
            record_type (Type[T]): The type of records to load, must be a subclass of RecordBase.
            key (str | int | list[str | int]): The key pattern to match.
            limit (int, optional): Maximum number of records to return.
            offset (int, optional): Number of records to skip.
            scan_count (int, optional): Number of keys to scan in each iteration.
            
        Returns:
            list[T]: A list of record instances loaded from Redis.
                    Returns an empty list if no records match.
        """
        hash_key = self.__collect_hash_key(category=record_type.category(), key=key)

        hash_keys = await self.__scan_hash_keys(hash_key, limit, offset, scan_count)
        if not hash_keys:
            return []

        pipeline = self._redis.pipeline()
        for key in hash_keys:
            pipeline.hgetall(key)

        results = await pipeline.execute()
        return await self.__process_loaded_records(record_type, hash_keys, results)

    async def delete(self, record_type: Type[T], key: str | int | list[str | int]) -> bool:
        """
        Deletes a record from Redis.
        
        Args:
            record_type (Type[T]): The type of record to delete, must be a subclass of RecordBase.
            key (str | int | list[str | int]): The key or key components that identify the record.
            
        Returns:
            bool: True if the record was deleted, False if it didn't exist.
        """
        hash_key = self.__collect_hash_key(category=record_type.category(), key=key)
        result = await self._redis.delete(hash_key)
        return bool(result)

    async def delete_many(self, record_type: Type[T], key: str | int | list[str | int]) -> int:
        """
        Deletes multiple records from Redis that match a pattern.
        
        Args:
            record_type (Type[T]): The type of records to delete, must be a subclass of RecordBase.
            key (str | int | list[str | int]): The key pattern to match.
            
        Returns:
            int: The number of records deleted.
        """
        hash_key = self.__collect_hash_key(category=record_type.category(), key=key)

        hash_keys = await self.__scan_hash_keys(hash_key)
        if not hash_keys:
            return 0

        pipeline = self._redis.pipeline()
        for hash_key in hash_keys:
            pipeline.delete(hash_key)

        results = await pipeline.execute()
        return sum(results)

    async def get_ttl(self, record_type: Type[T], key: str | int | list[str | int]) -> int | None:
        """
        Gets the remaining time-to-live for a record in Redis.
        
        Args:
            record_type (Type[T]): The type of record, must be a subclass of RecordBase.
            key (str | int | list[str | int]): The key or key components that identify the record.
            
        Returns:
            int | None: The remaining TTL in seconds, or None if the record doesn't exist.
                    Returns -1 if the record exists but has no expiration.
        """
        hash_key = self.__collect_hash_key(category=record_type.category(), key=key)
        ttl = await self._redis.ttl(hash_key)
        if ttl != -2:
            return ttl
        return None

    async def load_stream(self, record_type: Type[T], stream_key: str, start_time: int = None,
                          end_time: int = None, limit: int = None, event_type: StreamEvent = None) -> list[T]:
        """
        Loads records from a Redis stream within a specified time range.
        
        Args:
            record_type (Type[T]): The type of records to load, must be a subclass of RecordBase.
            stream_key (str): The stream key to load records from.
            start_time (int, optional): Start timestamp for the range. If None, starts from the beginning.
            end_time (int, optional): End timestamp for the range. If None, includes all entries to the latest.
            limit (int, optional): Maximum number of records to return.
            event_type (StreamEvent, optional): Filter records by event type (SAVE or UPDATE).
            
        Returns:
            list[T]: A list of record instances loaded from the stream.
                    Returns an empty list if no records match.
        """
        stream_hash_key = f"{record_type.category()}:{stream_key}:{DefaultKeys.STREAM_KEY.value}"

        start_id = f"{start_time}-0" if start_time is not None else "-"
        end_id = f"{end_time}-9999999" if end_time is not None else "+"

        events = await self._redis.xrange(stream_hash_key, start_id, end_id, count=limit)
        hash_keys = []
        for _, event_data in events:
            event = event_data["event"]
            if not event_type or (event_type and event_type.value == event):
                hash_keys.append(event_data["hash_key"])

        if not hash_keys:
            return []

        pipeline = self._redis.pipeline()
        for key in hash_keys:
            pipeline.hgetall(key)
        results = await pipeline.execute()

        return await self.__process_loaded_records(record_type, hash_keys, results)
