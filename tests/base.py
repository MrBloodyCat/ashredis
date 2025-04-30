import os
from datetime import timedelta
from time import time

import dotenv

from src.ashredis import RedisParams

dotenv.load_dotenv()

TEST_DATA = {
    "name": "Test Product",
    "price": 99.99,
    "stock": 100,
    "tags": ["electronics", "gadget"],
    "metadata": {"weight": 0.5, "color": "black"},
    "is_priority": True,
    "last_update_ts": int(time() * 1000)
}
REDIS_PARAMS = RedisParams(
    host=os.getenv("REDIS_HOST"),
    port=int(os.getenv("REDIS_PORT")),
    password=os.getenv("REDIS_PASSWORD"),
    db=int(os.getenv("REDIS_DB"))
)


class BaseRedisTest:
    """Base class for Redis object tests with common fixtures and utilities"""

    @classmethod
    def create_test_products(cls, count: int = 3, prefix: str = "test") -> list:
        """Generate test product data"""
        return [
            {
                "name": f"{prefix}_product_{i}",
                "price": 10.0 * (i + 1),
                "stock": 5 * (i + 1),
                "tags": ["tag1", f"tag{i}"],
                "metadata": {"index": i},
                "is_priority": bool(i % 2),
                "last_update_ts": int(time() * 1000)
            }
            for i in range(count)
        ]

    @classmethod
    def get_timestamp_range(cls, time_range: timedelta = None) -> tuple:
        """Get start and end timestamps for time-based tests"""
        if time_range is None:
            time_range = timedelta(minutes=5)

        end_ts = int(time() * 1000)
        start_ts = end_ts - int(time_range.total_seconds() * 1000)
        return start_ts, end_ts
