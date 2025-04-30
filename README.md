# ashredis - Redis Object Library
[![PyPI version](https://img.shields.io/pypi/v/ashredis.svg)](https://pypi.org/project/ashredis/)
[![Python versions](https://img.shields.io/pypi/pyversions/ashredis.svg)](https://pypi.org/project/ashredis/)
## Overview
Python library for Redis object storage with sync/async interfaces.
## Installation
```bash
pip install ashredis
```
## Defining Models
### Base Class Setup
```py
from ashredis import AsyncRedisObject, RedisParams

REDIS_PARAMS = RedisParams(
    host="localhost",
    port=6379,
    password="your_password",
    db=0
)

class AsyncRedisObject(AsyncRedisObject):
    """Base class for all async models"""
    def __init__(self, key: str | int = None, path: list[str] = None):
        super().__init__(redis_params=REDIS_PARAMS, key=key, path=path)
```
### Model Definition
```py
class Product(AsyncRedisObject):
    """Product model example"""
    name: str
    price: float
    stock: int
    tags: list
    metadata: dict
    is_priority: bool
    last_update_ts: int
    
    __category__ = "product"  # Redis key prefix
```
## Basic Operations
### Save
```py 
from datetime import timedelta, datetime

async with Product(key="prod_123") as p:
    p.name = "Wireless Headphones"
    p.price = 129.99
    p.stock = 25
    p.tags = ["audio", "wireless"]
    p.metadata = {"brand": "Sony", "color": "black"}
    p.is_priority = True
    p.last_update_ts = int(datetime.now().timestamp() * 1000)
    
    await p.save(ttl=timedelta(hours=2))  # Optional TTL
```
### Load
```py 
async with Product(key="prod_123") as p:
    if await p.load():
        print(f"Product: {p.name}")
        print(f"Price: ${p.price}")
        print(f"In Stock: {p.stock}")
```
### Update
```py 
async with Product(key="prod_123") as p:
    p.stock = 20
    await p.save()
```
### Delete
```py 
async with Product(key="prod_123") as p:
    if await p.delete():
        print("Product deleted successfully")
```
## Advanced Usage
### Hierarchical Keys
```py 
# Creates key "product:electronics:audio:prod_123"
async with Product(key="prod_123", path=["electronics", "audio"]) as p:
    p.name = "Studio Headphones"
    await p.save()
```
### Bulk Operations
```py 
# Get all products
all_products = await Product().load_all()

# Get sorted by price (descending)
expensive_first = await Product().load_sorted("price", reverse_sorted=True)

# Get recently updated
recent = await Product().load_for_time(
    ts_field="last_update_ts",
    time_range=timedelta(days=1)
)
```
### Copy
```py 
async with Product(key="prod_123") as p:
    await p.copy(p2)  # Copies all data from original
    p.price = 90.00
    await p.save()
```
### Data Conversion
```py 
# Export to dict
product_data = {
    "name": "Gaming Mouse",
    "price": 59.99,
    "stock": 30
}

async with Product(key="mouse_01") as p:
    p.load_dict(product_data)
    await p.save()
    
    # Verify
    exported = p.get_dict()
    print(exported)
```
### Get TTL
```py 
from datetime import timedelta

async with Product(key="temp_product") as p:
    p.name = "Temporary Offer"
    await p.save(ttl=timedelta(minutes=30))
    
    # Check remaining time
    ttl = await p.get_ttl()
    print(f"Product expires in {ttl} seconds")
```
### Stream In Interval
```py 
from datetime import datetime, timedelta

# Get events from specific time range
start_ts = int((datetime.now() - timedelta(hours=1)).timestamp() * 1000)
end_ts = int(datetime.now().timestamp() * 1000)
events = await Product().get_stream_in_interval(start_ts, end_ts)

for event in events:
    print(f"Event: {event.name} at {event.last_update_ts}")
```
### Stream Listening
```py 
async def handle_event(event):
    print(f"New product update: {event.name}")

# Start listening for events
async def monitor_updates():
    product = Product(path=["electronics"])
    await product.listen_for_stream(
        callback=handle_event,
        delay=1  # check every second
    )
```