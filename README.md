# ashredis - Redis Object Storage Library
[![PyPI version](https://img.shields.io/pypi/v/ashredis.svg)](https://pypi.org/project/ashredis/)
[![Python versions](https://img.shields.io/pypi/pyversions/ashredis.svg)](https://pypi.org/project/ashredis/)
## Overview
Python library for Redis object storage with async interface.
## Installation
```bash
pip install ashredis
```
## Basic Usage Example
```python
import asyncio
from dataclasses import dataclass
from typing import Optional
from ashredis import RedisObject, RedisParams, RecordBase, MISSING

# Define data model
@dataclass
class User(RecordBase):
    username: Optional[str] = MISSING
    email: Optional[str] = MISSING
    age: Optional[int] = MISSING

async def main():
    # Configure Redis connection
    redis_params = RedisParams(
        host="localhost",
        port=6379,
        password="",
        db=0
    )
    
    # Create RedisObject instance
    async with RedisObject(redis_params=redis_params) as redis_obj:
        # Create and save object
        user = User(
            username="test_user",
            email="user@example.com",
            age=30
        )
        
        # Save object to Redis
        await redis_obj.save(record=user, key="user_1")
        
        # Load object from Redis
        loaded_user = await redis_obj.load(record_type=User, key="user_1")
        print(f"Loaded user: {loaded_user.username}, {loaded_user.email}")
        
        # Update object
        loaded_user.age = 31
        await redis_obj.save(record=loaded_user, key="user_1")
        
        # Delete object
        await redis_obj.delete(record_type=User, key="user_1")

if __name__ == "__main__":
    asyncio.run(main())
```