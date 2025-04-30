from dataclasses import dataclass


@dataclass
class RedisParams:
    host: str
    port: int
    password: str
    db: int
