"""Cache module for TensorWall."""

from backend.adapters.cache.redis_client import (
    get_redis,
    init_redis,
    close_redis,
    RedisCache,
)

__all__ = [
    "get_redis",
    "init_redis",
    "close_redis",
    "RedisCache",
]
