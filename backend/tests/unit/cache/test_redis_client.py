"""Unit tests for Redis Cache Client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from backend.adapters.cache.redis_client import (
    RedisCache,
    init_redis,
    get_redis,
    close_redis,
    get_cache,
)


class TestRedisConnection:
    """Tests for Redis connection management."""

    @pytest.mark.asyncio
    async def test_init_redis(self):
        """Test initializing Redis connection."""
        with patch("backend.adapters.cache.redis_client.redis") as mock_redis:
            mock_client = AsyncMock()
            mock_redis.from_url.return_value = mock_client

            with patch("backend.adapters.cache.redis_client._redis_pool", None):
                await init_redis()
                mock_redis.from_url.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_redis_initializes_if_none(self):
        """Test get_redis initializes connection if not exists."""
        with patch("backend.adapters.cache.redis_client._redis_pool", None):
            with patch("backend.adapters.cache.redis_client.init_redis") as mock_init:
                mock_init.return_value = AsyncMock()
                await get_redis()
                mock_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_redis(self):
        """Test closing Redis connection."""
        mock_pool = AsyncMock()
        with patch("backend.adapters.cache.redis_client._redis_pool", mock_pool):
            await close_redis()
            mock_pool.close.assert_called_once()


class TestRedisCacheCredentials:
    """Tests for credentials caching."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_redis = AsyncMock()
        self.cache = RedisCache(self.mock_redis)

    @pytest.mark.asyncio
    async def test_get_credentials_found(self):
        """Test getting cached credentials when found."""
        creds = {"app_id": "test-app", "owner": "test-owner"}
        self.mock_redis.get.return_value = json.dumps(creds)

        result = await self.cache.get_credentials("key-hash")

        assert result == creds
        self.mock_redis.get.assert_called_once_with("creds:key-hash")

    @pytest.mark.asyncio
    async def test_get_credentials_not_found(self):
        """Test getting cached credentials when not found."""
        self.mock_redis.get.return_value = None

        result = await self.cache.get_credentials("key-hash")

        assert result is None

    @pytest.mark.asyncio
    async def test_set_credentials(self):
        """Test setting cached credentials."""
        creds = {"app_id": "test-app"}

        await self.cache.set_credentials("key-hash", creds, ttl_seconds=300)

        self.mock_redis.setex.assert_called_once_with(
            "creds:key-hash", 300, json.dumps(creds)
        )

    @pytest.mark.asyncio
    async def test_invalidate_credentials(self):
        """Test invalidating cached credentials."""
        await self.cache.invalidate_credentials("key-hash")

        self.mock_redis.delete.assert_called_once_with("creds:key-hash")


class TestRedisCacheBudget:
    """Tests for budget caching."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_redis = AsyncMock()
        self.cache = RedisCache(self.mock_redis)

    @pytest.mark.asyncio
    async def test_get_budget_spend_found(self):
        """Test getting budget spend when found."""
        self.mock_redis.get.return_value = "100.50"

        result = await self.cache.get_budget_spend("app-1")

        assert result == 100.50

    @pytest.mark.asyncio
    async def test_get_budget_spend_not_found(self):
        """Test getting budget spend when not found."""
        self.mock_redis.get.return_value = None

        result = await self.cache.get_budget_spend("app-1")

        assert result == 0.0

    @pytest.mark.asyncio
    async def test_get_budget_spend_with_feature(self):
        """Test getting budget spend with feature filter."""
        self.mock_redis.get.return_value = "50.0"

        await self.cache.get_budget_spend("app-1", feature="chat")

        # Note: PREFIX_BUDGET already includes colon, so key is budget::app-1:chat
        self.mock_redis.get.assert_called_once_with("budget::app-1:chat")

    @pytest.mark.asyncio
    async def test_get_budget_spend_with_environment(self):
        """Test getting budget spend with environment filter."""
        self.mock_redis.get.return_value = "25.0"

        await self.cache.get_budget_spend(
            "app-1", feature="chat", environment="production"
        )

        self.mock_redis.get.assert_called_once_with("budget::app-1:chat:production")

    @pytest.mark.asyncio
    async def test_increment_budget_spend(self):
        """Test incrementing budget spend."""
        self.mock_redis.incrbyfloat.return_value = 15000  # $150.00 in cents
        self.mock_redis.ttl.return_value = 86400

        result = await self.cache.increment_budget_spend("app-1", 50.0)

        assert result == 150.0

    @pytest.mark.asyncio
    async def test_increment_budget_spend_sets_ttl_if_new(self):
        """Test that TTL is set for new budget keys."""
        self.mock_redis.incrbyfloat.return_value = 5000
        self.mock_redis.ttl.return_value = -1  # No TTL set

        await self.cache.increment_budget_spend("app-1", 50.0)

        self.mock_redis.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_budget_spend(self):
        """Test resetting budget spend."""
        await self.cache.reset_budget_spend("app-1")

        self.mock_redis.delete.assert_called_once_with("budget::app-1")


class TestRedisCacheRateLimiting:
    """Tests for rate limiting."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_redis = MagicMock()
        self.cache = RedisCache(self.mock_redis)

    @pytest.mark.asyncio
    async def test_check_rate_limit_allowed(self):
        """Test rate limit check when under limit."""
        # Create a mock pipeline that returns a MagicMock for chaining
        mock_pipe = MagicMock()
        mock_pipe.incr.return_value = mock_pipe
        mock_pipe.expire.return_value = mock_pipe
        mock_pipe.ttl.return_value = mock_pipe
        mock_pipe.execute = AsyncMock(return_value=[5, True, 60])  # count=5
        self.mock_redis.pipeline.return_value = mock_pipe

        allowed, count, remaining = await self.cache.check_rate_limit(
            "user:123", limit=10, window_seconds=60
        )

        assert allowed is True
        assert count == 5
        assert remaining == 5

    @pytest.mark.asyncio
    async def test_check_rate_limit_exceeded(self):
        """Test rate limit check when over limit."""
        mock_pipe = MagicMock()
        mock_pipe.incr.return_value = mock_pipe
        mock_pipe.expire.return_value = mock_pipe
        mock_pipe.ttl.return_value = mock_pipe
        mock_pipe.execute = AsyncMock(return_value=[15, True, 30])  # count=15
        self.mock_redis.pipeline.return_value = mock_pipe

        allowed, count, remaining = await self.cache.check_rate_limit(
            "user:123", limit=10, window_seconds=60
        )

        assert allowed is False
        assert count == 15
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_get_rate_limit_status(self):
        """Test getting rate limit status."""
        mock_pipe = MagicMock()
        mock_pipe.get.return_value = mock_pipe
        mock_pipe.ttl.return_value = mock_pipe
        mock_pipe.execute = AsyncMock(return_value=["5", 45])  # count=5, ttl=45
        self.mock_redis.pipeline.return_value = mock_pipe

        status = await self.cache.get_rate_limit_status("user:123", limit=10)

        assert status["current"] == 5
        assert status["limit"] == 10
        assert status["remaining"] == 5
        assert status["reset_in_seconds"] == 45

    @pytest.mark.asyncio
    async def test_get_rate_limit_status_empty(self):
        """Test getting rate limit status when no requests made."""
        mock_pipe = MagicMock()
        mock_pipe.get.return_value = mock_pipe
        mock_pipe.ttl.return_value = mock_pipe
        mock_pipe.execute = AsyncMock(return_value=[None, -1])  # No count, no TTL
        self.mock_redis.pipeline.return_value = mock_pipe

        status = await self.cache.get_rate_limit_status("user:123", limit=10)

        assert status["current"] == 0
        assert status["remaining"] == 10
        assert status["reset_in_seconds"] == 0


class TestRedisCachePolicies:
    """Tests for policy caching."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_redis = AsyncMock()
        self.cache = RedisCache(self.mock_redis)

    @pytest.mark.asyncio
    async def test_get_policies_found(self):
        """Test getting cached policies when found."""
        policies = [{"name": "policy-1"}, {"name": "policy-2"}]
        self.mock_redis.get.return_value = json.dumps(policies)

        result = await self.cache.get_policies("app-1")

        assert result == policies

    @pytest.mark.asyncio
    async def test_get_policies_not_found(self):
        """Test getting cached policies when not found."""
        self.mock_redis.get.return_value = None

        result = await self.cache.get_policies("app-1")

        assert result is None

    @pytest.mark.asyncio
    async def test_set_policies(self):
        """Test setting cached policies."""
        policies = [{"name": "policy-1"}]

        await self.cache.set_policies("app-1", policies)

        self.mock_redis.setex.assert_called_once_with(
            "policy:app-1", 60, json.dumps(policies)
        )

    @pytest.mark.asyncio
    async def test_invalidate_policies(self):
        """Test invalidating cached policies."""
        await self.cache.invalidate_policies("app-1")

        self.mock_redis.delete.assert_called_once_with("policy:app-1")


class TestRedisCacheGenericOperations:
    """Tests for generic cache operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_redis = AsyncMock()
        self.cache = RedisCache(self.mock_redis)

    @pytest.mark.asyncio
    async def test_get(self):
        """Test generic get operation."""
        self.mock_redis.get.return_value = "value"

        result = await self.cache.get("key")

        assert result == "value"

    @pytest.mark.asyncio
    async def test_set_with_ttl(self):
        """Test generic set operation with TTL."""
        await self.cache.set("key", {"data": "value"}, ttl_seconds=300)

        self.mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_without_ttl(self):
        """Test generic set operation without TTL."""
        await self.cache.set("key", {"data": "value"})

        self.mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete(self):
        """Test generic delete operation."""
        await self.cache.delete("key")

        self.mock_redis.delete.assert_called_once_with("key")

    @pytest.mark.asyncio
    async def test_exists_true(self):
        """Test exists check when key exists."""
        self.mock_redis.exists.return_value = 1

        result = await self.cache.exists("key")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self):
        """Test exists check when key does not exist."""
        self.mock_redis.exists.return_value = 0

        result = await self.cache.exists("key")

        assert result is False


class TestGetCache:
    """Tests for get_cache helper."""

    @pytest.mark.asyncio
    async def test_get_cache(self):
        """Test getting cache instance."""
        mock_redis = AsyncMock()
        with patch(
            "backend.adapters.cache.redis_client.get_redis", return_value=mock_redis
        ):
            cache = await get_cache()

            assert isinstance(cache, RedisCache)
            assert cache.redis == mock_redis
