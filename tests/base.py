import os
import unittest
from time import time

import dotenv
from redis.asyncio import Redis

from src.ashredis.models import RedisParams
from src.ashredis.object_redis import RedisObject
from tests.models import ComplexTestModel, NestedLevel1, NestedLevel2, NestedLevel3

dotenv.load_dotenv()

REDIS_PARAMS = RedisParams(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    password=os.getenv("REDIS_PASSWORD", ""),
    db=int(os.getenv("REDIS_DB", 0))
)


def create_complex_model():
    nested3 = NestedLevel3(
        value="Deep Value",
        number=999,
        flag=True
    )

    nested2 = NestedLevel2(
        name="Nested Name",
        count=5,
        nested3=nested3,
        items=["a", "b", "c"]
    )

    nested1 = NestedLevel1(
        title="Nested Title",
        nested2=nested2,
        values={"x": 1, "y": 2, "z": 3},
        created_at=int(time() * 1000)
    )

    return ComplexTestModel(
        string_field="Test String",
        integer_field=42,
        float_field=3.14159,
        boolean_field=True,
        list_field=["item1", "item2", "item3"],
        dict_field={"key1": "value1", "key2": 2},
        nested_field=nested1,
        timestamp=int(time() * 1000)
    )


async def cleanup_redis(pattern="ComplexTestModel:*"):
    async with Redis(**REDIS_PARAMS.__dict__, decode_responses=True) as redis:
        keys = await redis.keys(pattern)
        if keys:
            await redis.delete(*keys)


class BaseRedisTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await cleanup_redis()

        self.redis_obj = RedisObject(redis_params=REDIS_PARAMS)
        await self.redis_obj.__aenter__()

        self.test_model = create_complex_model()
        self.test_key = "test_key"
        self.test_list_key = ["test", "list", "key"]

    async def asyncTearDown(self):
        await self.redis_obj.__aexit__(None, None, None)
        await cleanup_redis()
