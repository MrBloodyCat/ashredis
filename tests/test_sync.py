import unittest
from datetime import timedelta

from src.ashredis import SyncRedisObject as TestSyncRedisObject
from tests.base import BaseRedisTest, TEST_DATA, REDIS_PARAMS


class SyncRedisObject(TestSyncRedisObject):
    """Base class for all sync models"""
    def __init__(self, key: str | int = None, path: list[str] = None):
        super().__init__(redis_params=REDIS_PARAMS, key=key, path=path)


class SyncTestCategory(SyncRedisObject):
    """Test model for sync RedisObject implementation"""
    name: str
    price: float
    stock: int
    tags: list
    metadata: dict
    is_priority: bool
    last_update_ts: int

    __category__ = "test_product"


class TestSyncRedisObject(unittest.TestCase, BaseRedisTest):
    """Test suite for SyncRedisObject functionality"""

    def setUp(self):
        """Initialize test environment"""
        self.test_key = "sync_test"
        self.test_path = ["test", "path"]
        self.obj = SyncTestCategory(
            key=self.test_key,
            path=self.test_path
        )

    def tearDown(self):
        """Clean up test data"""
        if hasattr(self, 'obj'):
            self.obj.delete()

    def test_basic_operations(self):
        """Test basic CRUD operations"""
        self.obj.name = TEST_DATA["name"]
        self.obj.price = TEST_DATA["price"]
        self.obj.save()

        loaded = self.obj.load()
        self.assertTrue(loaded)
        self.assertEqual(self.obj.name, TEST_DATA["name"])
        self.assertEqual(self.obj.price, TEST_DATA["price"])

        deleted = self.obj.delete()
        self.assertTrue(deleted)
        self.assertFalse(self.obj.load())

    def test_time_based_operations(self):
        """Test time-based operations"""
        test_products = self.create_test_products(3)
        for product in test_products:
            obj = SyncTestCategory(
                path=self.test_path,
                key=product["name"].replace(" ", "_")
            )
            obj.load_dict(product)
            obj.save()

        start_ts, end_ts = self.get_timestamp_range()
        time_based = self.obj.load_for_time(
            ts_field="last_update_ts",
            time_range=timedelta(minutes=5)
        )
        self.assertGreaterEqual(len(time_based), 3)

        stream_data = self.obj.get_stream_in_interval(start_ts, end_ts)
        self.assertIsInstance(stream_data, list)

        for product in test_products:
            obj = SyncTestCategory(
                key=product["name"].replace(" ", "_")
            )
            obj.delete()

    def test_data_conversion_methods(self):
        """Test data conversion methods"""
        self.obj.load_dict(TEST_DATA)
        self.assertEqual(self.obj.name, TEST_DATA["name"])

        data_dict = self.obj.get_dict()
        self.assertDictEqual(data_dict, TEST_DATA)

        new_obj = SyncTestCategory()
        new_obj.copy(self.obj)
        self.assertEqual(new_obj.name, self.obj.name)

    def test_pagination_and_sorting(self):
        """Test pagination and sorting options"""
        test_products = self.create_test_products(5)

        for product in test_products:
            obj = SyncTestCategory(
                path=self.test_path,
                key=product["name"].replace(" ", "_")
            )
            obj.load_dict(product)
            obj.save()

        all_items = self.obj.load_all(offset=1, limit=2)
        self.assertEqual(len(all_items), 2)

        sorted_items = self.obj.load_sorted("price", reverse_sorted=True)
        prices = [item.price for item in sorted_items]
        self.assertEqual(prices, sorted(prices))

        for product in test_products:
            obj = SyncTestCategory(
                key=product["name"].replace(" ", "_")
            )
            obj.delete()
