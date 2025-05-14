import asyncio
import unittest
from datetime import timedelta
from time import time

from src.ashredis.enums import StreamEvent
from tests.base import BaseRedisTest, ComplexTestModel, create_complex_model


class TestAdvancedOperations(BaseRedisTest):
    async def test_save_with_ttl(self):
        ttl = timedelta(seconds=2)
        await self.redis_obj.save(record=self.test_model, key=self.test_key, ttl=ttl)

        loaded_model = await self.redis_obj.load(record_type=ComplexTestModel, key=self.test_key)
        self.assertIsNotNone(loaded_model)

        await asyncio.sleep(3)

        loaded_model = await self.redis_obj.load(record_type=ComplexTestModel, key=self.test_key)
        self.assertIsNone(loaded_model)

    async def test_save_with_stream(self):
        stream_key = "test_stream"

        await self.redis_obj.save(record=self.test_model, key=self.test_key, stream_key=stream_key)

        stream_records = await self.redis_obj.load_stream(
            record_type=ComplexTestModel,
            stream_key=stream_key
        )

        self.assertEqual(len(stream_records), 1)
        self.assertEqual(stream_records[0].string_field, self.test_model.string_field)

    async def test_save_many_with_ttl_and_stream(self):
        models = [create_complex_model() for _ in range(3)]
        keys = ["key1", "key2", "key3"]
        ttl = timedelta(seconds=2)
        stream_key = "test_stream_many"

        await self.redis_obj.save_many(records=models, keys=keys, ttl=ttl, stream_key=stream_key)

        stream_records = await self.redis_obj.load_stream(
            record_type=ComplexTestModel,
            stream_key=stream_key
        )
        self.assertEqual(len(stream_records), 3)

        await asyncio.sleep(3)

        for key in keys:
            loaded_model = await self.redis_obj.load(record_type=ComplexTestModel, key=key)
            self.assertIsNone(loaded_model)

    async def test_load_stream_with_filters(self):
        stream_key = "test_stream_filters"

        for i in range(3):
            model = create_complex_model()
            model.string_field = f"Stream Model {i}"
            await self.redis_obj.save(record=model, key=f"stream_key_{i}", stream_key=stream_key)
            await asyncio.sleep(0.1)

        current_time = int(time() * 1000)
        start_time = current_time - 10000

        stream_records = await self.redis_obj.load_stream(
            record_type=ComplexTestModel,
            stream_key=stream_key,
            start_time=start_time,
            end_time=current_time,
            limit=2,
            event_type=StreamEvent.SAVE
        )

        self.assertLessEqual(len(stream_records), 2)

    async def test_update_with_stream(self):
        await self.redis_obj.save(record=self.test_model, key=self.test_key)

        loaded_model = await self.redis_obj.load(record_type=ComplexTestModel, key=self.test_key)
        loaded_model.string_field = "Updated String"
        
        await self.redis_obj.save(record=loaded_model, key=self.test_key, stream_key="update_stream")

        stream_records = await self.redis_obj.load_stream(
            record_type=ComplexTestModel,
            stream_key="update_stream",
            event_type=StreamEvent.UPDATE
        )
        self.assertEqual(len(stream_records), 1)


if __name__ == "__main__":
    unittest.main()