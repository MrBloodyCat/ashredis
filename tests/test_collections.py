import unittest

from tests.base import BaseRedisTest, ComplexTestModel, create_complex_model


class TestCollectionOperations(BaseRedisTest):
    async def test_save_many(self):
        models = [create_complex_model() for _ in range(3)]
        keys = ["key1", "key2", "key3"]

        await self.redis_obj.save_many(records=models, keys=keys)

        for i, key in enumerate(keys):
            loaded_model = await self.redis_obj.load(record_type=ComplexTestModel, key=key)
            self.assertIsNotNone(loaded_model)
            self.assertEqual(loaded_model.string_field, models[i].string_field)

    async def test_load_many(self):
        for i in range(5):
            model = create_complex_model()
            model.string_field = f"Model {i}"
            await self.redis_obj.save(record=model, key=f"test_key_{i}")

        loaded_models = await self.redis_obj.load_many(
            record_type=ComplexTestModel,
            key="test_key_*"
        )

        self.assertEqual(len(loaded_models), 5)

        limited_models = await self.redis_obj.load_many(
            record_type=ComplexTestModel,
            key="test_key_*",
            limit=2,
            offset=1
        )
        self.assertEqual(len(limited_models), 2)

    async def test_delete_many(self):
        for i in range(5):
            model = create_complex_model()
            model.string_field = f"Model {i}"
            await self.redis_obj.save(record=model, key=f"test_key_{i}")

        count = await self.redis_obj.delete_many(record_type=ComplexTestModel, key="test_key_*")
        self.assertEqual(count, 5)

        loaded_models = await self.redis_obj.load_many(
            record_type=ComplexTestModel,
            key="test_key_*"
        )
        self.assertEqual(len(loaded_models), 0)

    async def test_complex_key_types(self):
        await self.redis_obj.save(record=self.test_model, key="string_key")
        loaded_model = await self.redis_obj.load(record_type=ComplexTestModel, key="string_key")
        self.assertIsNotNone(loaded_model)

        await self.redis_obj.save(record=self.test_model, key=12345)
        loaded_model = await self.redis_obj.load(record_type=ComplexTestModel, key=12345)
        self.assertIsNotNone(loaded_model)

        await self.redis_obj.save(record=self.test_model, key=["part1", "part2", 3])
        loaded_model = await self.redis_obj.load(record_type=ComplexTestModel, key=["part1", "part2", 3])
        self.assertIsNotNone(loaded_model)


if __name__ == "__main__":
    unittest.main()