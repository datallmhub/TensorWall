"""Redis client for caching and rate limiting."""

import json
from typing import Optional, Any
import redis.asyncio as redis

from backend.core.config import settings


# Global Redis connection pool
_redis_pool: Optional[redis.Redis] = None


async def init_redis() -> redis.Redis:
    """Initialize Redis connection pool."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_pool


async def get_redis() -> redis.Redis:
    """Get Redis connection."""
    if _redis_pool is None:
        await init_redis()
    return _redis_pool


async def close_redis() -> None:
    """Close Redis connection pool."""
    global _redis_pool
    if _redis_pool:
        await _redis_pool.close()
        _redis_pool = None


class RedisCache:
    """High-level cache operations."""

    # Key prefixes
    PREFIX_CREDENTIALS = "creds:"
    PREFIX_BUDGET = "budget:"
    PREFIX_RATE_LIMIT = "rate:"
    PREFIX_POLICY = "policy:"

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    # =========================================================================
    # Credentials Cache
    # =========================================================================

    async def get_credentials(self, api_key_hash: str) -> Optional[dict]:
        """Get cached credentials by API key hash."""
        key = f"{self.PREFIX_CREDENTIALS}{api_key_hash}"
        data = await self.redis.get(key)
        if data:
            return json.loads(data)
        return None

    async def set_credentials(
        self,
        api_key_hash: str,
        credentials: dict,
        ttl_seconds: int = 300,  # 5 minutes
    ) -> None:
        """Cache credentials."""
        key = f"{self.PREFIX_CREDENTIALS}{api_key_hash}"
        await self.redis.setex(key, ttl_seconds, json.dumps(credentials))

    async def invalidate_credentials(self, api_key_hash: str) -> None:
        """Invalidate cached credentials."""
        key = f"{self.PREFIX_CREDENTIALS}{api_key_hash}"
        await self.redis.delete(key)

    # =========================================================================
    # Budget Tracking
    # =========================================================================

    async def get_budget_spend(
        self,
        app_id: str,
        feature: Optional[str] = None,
        environment: Optional[str] = None,
    ) -> float:
        """Get current budget spend from cache."""
        key = self._budget_key(app_id, feature, environment)
        spend = await self.redis.get(key)
        return float(spend) if spend else 0.0

    async def increment_budget_spend(
        self,
        app_id: str,
        amount: float,
        feature: Optional[str] = None,
        environment: Optional[str] = None,
        ttl_seconds: int = 86400 * 31,  # 31 days
    ) -> float:
        """Increment budget spend and return new total."""
        key = self._budget_key(app_id, feature, environment)

        # Use INCRBYFLOAT for atomic increment
        # Convert to cents for precision
        amount_cents = int(amount * 100)
        new_cents = await self.redis.incrbyfloat(key, amount_cents)

        # Set TTL if key is new
        ttl = await self.redis.ttl(key)
        if ttl == -1:  # No expiry set
            await self.redis.expire(key, ttl_seconds)

        return float(new_cents) / 100

    async def reset_budget_spend(
        self,
        app_id: str,
        feature: Optional[str] = None,
        environment: Optional[str] = None,
    ) -> None:
        """Reset budget spend to zero."""
        key = self._budget_key(app_id, feature, environment)
        await self.redis.delete(key)

    def _budget_key(
        self,
        app_id: str,
        feature: Optional[str],
        environment: Optional[str],
    ) -> str:
        """Build budget cache key."""
        parts = [self.PREFIX_BUDGET, app_id]
        if feature:
            parts.append(feature)
        if environment:
            parts.append(environment)
        return ":".join(parts)

    # =========================================================================
    # Rate Limiting
    # =========================================================================

    async def check_rate_limit(
        self,
        identifier: str,
        limit: int,
        window_seconds: int = 60,
    ) -> tuple[bool, int, int]:
        """
        Check rate limit using sliding window.
        Returns: (allowed, current_count, remaining)
        """
        key = f"{self.PREFIX_RATE_LIMIT}{identifier}"

        # Use Redis pipeline for atomic operations
        pipe = self.redis.pipeline()

        # Increment counter
        pipe.incr(key)
        # Set expiry if new key
        pipe.expire(key, window_seconds, nx=True)
        # Get TTL
        pipe.ttl(key)

        results = await pipe.execute()
        current_count = results[0]
        # results[2] is TTL, not needed here

        allowed = current_count <= limit
        remaining = max(0, limit - current_count)

        return allowed, current_count, remaining

    async def get_rate_limit_status(
        self,
        identifier: str,
        limit: int,
    ) -> dict:
        """Get current rate limit status."""
        key = f"{self.PREFIX_RATE_LIMIT}{identifier}"

        pipe = self.redis.pipeline()
        pipe.get(key)
        pipe.ttl(key)
        results = await pipe.execute()

        current_count = int(results[0]) if results[0] else 0
        ttl = results[1] if results[1] > 0 else 0

        return {
            "current": current_count,
            "limit": limit,
            "remaining": max(0, limit - current_count),
            "reset_in_seconds": ttl,
        }

    # =========================================================================
    # Policy Cache
    # =========================================================================

    async def get_policies(self, app_id: str) -> Optional[list[dict]]:
        """Get cached policies for an application."""
        key = f"{self.PREFIX_POLICY}{app_id}"
        data = await self.redis.get(key)
        if data:
            return json.loads(data)
        return None

    async def set_policies(
        self,
        app_id: str,
        policies: list[dict],
        ttl_seconds: int = 60,  # 1 minute
    ) -> None:
        """Cache policies for an application."""
        key = f"{self.PREFIX_POLICY}{app_id}"
        await self.redis.setex(key, ttl_seconds, json.dumps(policies))

    async def invalidate_policies(self, app_id: str) -> None:
        """Invalidate cached policies."""
        key = f"{self.PREFIX_POLICY}{app_id}"
        await self.redis.delete(key)

    # =========================================================================
    # Generic Cache Operations
    # =========================================================================

    async def get(self, key: str) -> Optional[str]:
        """Get a value from cache."""
        return await self.redis.get(key)

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Set a value in cache."""
        if ttl_seconds:
            await self.redis.setex(key, ttl_seconds, json.dumps(value))
        else:
            await self.redis.set(key, json.dumps(value))

    async def delete(self, key: str) -> None:
        """Delete a key from cache."""
        await self.redis.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        return await self.redis.exists(key) > 0


# Helper to get cache instance
async def get_cache() -> RedisCache:
    """Get Redis cache instance."""
    redis_client = await get_redis()
    return RedisCache(redis_client)
