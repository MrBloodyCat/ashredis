import unittest

from tests.base import BaseRedisTest, ComplexTestModel
from src.ashredis.record_base import MISSING


class TestBasicOperations(BaseRedisTest):
    async def test_save_and_load(self):
        await self.redis_obj.save(record=self.test_model, key=self.test_key)

        loaded_model = await self.redis_obj.load(record_type=ComplexTestModel, key=self.test_key)

        self.assertIsNotNone(loaded_model)
        self.assertEqual(loaded_model.string_field, self.test_model.string_field)
        self.assertEqual(loaded_model.integer_field, self.test_model.integer_field)
        self.assertEqual(loaded_model.float_field, self.test_model.float_field)
        self.assertEqual(loaded_model.boolean_field, self.test_model.boolean_field)
        self.assertEqual(loaded_model.list_field, self.test_model.list_field)
        self.assertEqual(loaded_model.dict_field, self.test_model.dict_field)

        self.assertEqual(loaded_model.nested_field.title, self.test_model.nested_field.title)
        self.assertEqual(loaded_model.nested_field.nested2.name, self.test_model.nested_field.nested2.name)
        self.assertEqual(loaded_model.nested_field.nested2.count, self.test_model.nested_field.nested2.count)
        self.assertEqual(loaded_model.nested_field.nested2.nested3.value,
                         self.test_model.nested_field.nested2.nested3.value)
        self.assertEqual(loaded_model.nested_field.nested2.nested3.number,
                         self.test_model.nested_field.nested2.nested3.number)
        self.assertEqual(loaded_model.nested_field.nested2.nested3.flag,
                         self.test_model.nested_field.nested2.nested3.flag)

    async def test_delete(self):
        await self.redis_obj.save(record=self.test_model, key=self.test_key)

        loaded_model = await self.redis_obj.load(record_type=ComplexTestModel, key=self.test_key)
        self.assertIsNotNone(loaded_model)

        result = await self.redis_obj.delete(record_type=ComplexTestModel, key=self.test_key)
        self.assertTrue(result)

        loaded_model = await self.redis_obj.load(record_type=ComplexTestModel, key=self.test_key)
        self.assertIsNone(loaded_model)

        result = await self.redis_obj.delete(record_type=ComplexTestModel, key="non_existent_key")
        self.assertFalse(result)

    async def test_update_record(self):
        await self.redis_obj.save(record=self.test_model, key=self.test_key)

        loaded_model = await self.redis_obj.load(record_type=ComplexTestModel, key=self.test_key)

        loaded_model.string_field = "Updated String"
        loaded_model.integer_field = 100
        loaded_model.nested_field.title = "Updated Title"
        loaded_model.nested_field.nested2.nested3.value = "Updated Deep Value"

        await self.redis_obj.save(record=loaded_model, key=self.test_key)

        updated_model = await self.redis_obj.load(record_type=ComplexTestModel, key=self.test_key)

        self.assertEqual(updated_model.string_field, "Updated String")
        self.assertEqual(updated_model.integer_field, 100)
        self.assertEqual(updated_model.nested_field.title, "Updated Title")
        self.assertEqual(updated_model.nested_field.nested2.nested3.value, "Updated Deep Value")

    async def test_null_fields(self):
        model = self.test_model
        model.string_field = None
        model.nested_field.nested2.items = None

        await self.redis_obj.save(record=model, key=self.test_key)

        loaded_model = await self.redis_obj.load(record_type=ComplexTestModel, key=self.test_key)

        string_field = None if loaded_model.string_field is MISSING else loaded_model.string_field
        items = None if loaded_model.nested_field.nested2.items is MISSING else loaded_model.nested_field.nested2.items
        self.assertIsNone(string_field)
        self.assertIsNone(items)

        self.assertEqual(loaded_model.integer_field, model.integer_field)


if __name__ == "__main__":
    unittest.main()