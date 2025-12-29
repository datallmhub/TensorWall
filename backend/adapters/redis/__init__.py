"""Redis Adapters - Implémentations natives.

Architecture Hexagonale: Ces adapters implémentent les Ports de cache
en utilisant directement redis.asyncio.
"""

from backend.adapters.redis.cache_adapter import (
    RedisCacheAdapter,
    InMemoryCacheAdapter,
    create_redis_cache_adapter,
)


__all__ = [
    "RedisCacheAdapter",
    "InMemoryCacheAdapter",
    "create_redis_cache_adapter",
]
