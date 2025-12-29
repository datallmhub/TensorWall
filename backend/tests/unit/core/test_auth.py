"""Unit tests for Core Auth module."""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from backend.core.auth import (
    AppCredentials,
    AuthResult,
    hash_api_key,
    get_key_prefix,
    get_credentials_from_cache,
    cache_credentials,
    invalidate_credentials_cache,
    CREDENTIALS_CACHE_TTL,
)


class TestAppCredentials:
    """Tests for AppCredentials model."""

    def test_create_minimal(self):
        """Test creating credentials with required fields only."""
        creds = AppCredentials(
            app_id="test-app",
            api_key_id=1,
            api_key_prefix="gw_test_1234",
            owner="test-owner",
            environment="development",
            created_at=datetime.now(),
        )

        assert creds.app_id == "test-app"
        assert creds.is_active is True
        assert creds.allowed_providers == ["openai", "anthropic"]
        assert creds.allowed_models == []

    def test_create_full(self):
        """Test creating credentials with all fields."""
        now = datetime.now()
        creds = AppCredentials(
            app_id="test-app",
            api_key_id=1,
            api_key_prefix="gw_test_1234",
            owner="test-owner",
            environment="production",
            created_at=now,
            is_active=True,
            llm_api_key="sk-12345",
            allowed_providers=["openai"],
            allowed_models=["gpt-4", "gpt-3.5-turbo"],
        )

        assert creds.llm_api_key == "sk-12345"
        assert creds.allowed_providers == ["openai"]
        assert len(creds.allowed_models) == 2

    def test_from_dict(self):
        """Test creating credentials from dict."""
        data = {
            "app_id": "test-app",
            "api_key_id": 1,
            "api_key_prefix": "gw_test_1234",
            "owner": "test-owner",
            "environment": "development",
            "created_at": datetime.now().isoformat(),
        }
        creds = AppCredentials(**data)

        assert creds.app_id == "test-app"


class TestAuthResult:
    """Tests for AuthResult model."""

    def test_success_result(self):
        """Test successful auth result."""
        creds = AppCredentials(
            app_id="test-app",
            api_key_id=1,
            api_key_prefix="gw_test_1234",
            owner="test-owner",
            environment="development",
            created_at=datetime.now(),
        )
        result = AuthResult(
            authenticated=True,
            app_id="test-app",
            credentials=creds,
        )

        assert result.authenticated is True
        assert result.error is None
        assert result.credentials is not None

    def test_failure_result(self):
        """Test failed auth result."""
        result = AuthResult(
            authenticated=False,
            error="Invalid API key",
            error_code="INVALID_KEY",
        )

        assert result.authenticated is False
        assert result.error == "Invalid API key"
        assert result.error_code == "INVALID_KEY"
        assert result.credentials is None


class TestHashApiKey:
    """Tests for hash_api_key function."""

    def test_hash_produces_consistent_output(self):
        """Test that hashing is consistent."""
        key = "gw_test_1234567890abcdef"
        hash1 = hash_api_key(key)
        hash2 = hash_api_key(key)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex digest

    def test_hash_different_keys_produce_different_hashes(self):
        """Test that different keys produce different hashes."""
        hash1 = hash_api_key("key1")
        hash2 = hash_api_key("key2")

        assert hash1 != hash2

    def test_hash_empty_key(self):
        """Test hashing empty key."""
        result = hash_api_key("")
        assert len(result) == 64


class TestGetKeyPrefix:
    """Tests for get_key_prefix function."""

    def test_long_key_returns_12_chars(self):
        """Test that long keys return first 12 chars."""
        key = "gw_test_1234567890abcdef"
        prefix = get_key_prefix(key)

        assert prefix == "gw_test_1234"
        assert len(prefix) == 12

    def test_short_key_returns_full_key(self):
        """Test that short keys return the full key."""
        key = "short"
        prefix = get_key_prefix(key)

        assert prefix == "short"

    def test_exactly_12_chars(self):
        """Test key with exactly 12 chars."""
        key = "123456789012"
        prefix = get_key_prefix(key)

        assert prefix == key


class TestCacheOperations:
    """Tests for cache operations."""

    @pytest.mark.asyncio
    async def test_get_credentials_from_cache_found(self):
        """Test getting cached credentials when found."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = '{"app_id": "test-app", "owner": "test"}'

        with patch("backend.core.auth.get_redis", return_value=mock_redis):
            result = await get_credentials_from_cache("key-hash")

            assert result is not None
            assert result["app_id"] == "test-app"

    @pytest.mark.asyncio
    async def test_get_credentials_from_cache_not_found(self):
        """Test getting cached credentials when not found."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None

        with patch("backend.core.auth.get_redis", return_value=mock_redis):
            result = await get_credentials_from_cache("key-hash")

            assert result is None

    @pytest.mark.asyncio
    async def test_get_credentials_from_cache_redis_none(self):
        """Test getting cached credentials when Redis is None."""
        with patch("backend.core.auth.get_redis", return_value=None):
            result = await get_credentials_from_cache("key-hash")

            assert result is None

    @pytest.mark.asyncio
    async def test_get_credentials_from_cache_redis_error(self):
        """Test getting cached credentials when Redis throws error."""
        with patch("backend.core.auth.get_redis", side_effect=Exception("Redis error")):
            result = await get_credentials_from_cache("key-hash")

            assert result is None

    @pytest.mark.asyncio
    async def test_cache_credentials(self):
        """Test caching credentials."""
        mock_redis = AsyncMock()
        creds = {"app_id": "test-app", "owner": "test"}

        with patch("backend.core.auth.get_redis", return_value=mock_redis):
            await cache_credentials("key-hash", creds)

            mock_redis.setex.assert_called_once()
            call_args = mock_redis.setex.call_args[0]
            assert call_args[0] == "auth:credentials:key-hash"
            assert call_args[1] == CREDENTIALS_CACHE_TTL

    @pytest.mark.asyncio
    async def test_cache_credentials_redis_none(self):
        """Test caching credentials when Redis is None."""
        with patch("backend.core.auth.get_redis", return_value=None):
            # Should not raise
            await cache_credentials("key-hash", {"app_id": "test"})

    @pytest.mark.asyncio
    async def test_cache_credentials_redis_error(self):
        """Test caching credentials when Redis throws error."""
        with patch("backend.core.auth.get_redis", side_effect=Exception("Redis error")):
            # Should not raise
            await cache_credentials("key-hash", {"app_id": "test"})

    @pytest.mark.asyncio
    async def test_invalidate_credentials_cache(self):
        """Test invalidating cached credentials."""
        mock_redis = AsyncMock()

        with patch("backend.core.auth.get_redis", return_value=mock_redis):
            await invalidate_credentials_cache("key-hash")

            mock_redis.delete.assert_called_once_with("auth:credentials:key-hash")

    @pytest.mark.asyncio
    async def test_invalidate_credentials_cache_redis_none(self):
        """Test invalidating when Redis is None."""
        with patch("backend.core.auth.get_redis", return_value=None):
            # Should not raise
            await invalidate_credentials_cache("key-hash")

    @pytest.mark.asyncio
    async def test_invalidate_credentials_cache_redis_error(self):
        """Test invalidating when Redis throws error."""
        with patch("backend.core.auth.get_redis", side_effect=Exception("Redis error")):
            # Should not raise
            await invalidate_credentials_cache("key-hash")
