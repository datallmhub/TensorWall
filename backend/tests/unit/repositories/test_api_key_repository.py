"""Unit tests for API Key Repository."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta

from backend.db.repositories.api_key import (
    ApiKeyRepository,
    hash_api_key,
    generate_api_key,
)
from backend.db.models import ApiKey, Environment


class TestHashApiKey:
    """Tests for hash_api_key function."""

    def test_hash_produces_consistent_output(self):
        """Test that hashing is consistent."""
        key = "gw_test_1234567890"
        hash1 = hash_api_key(key)
        hash2 = hash_api_key(key)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex digest

    def test_hash_different_keys_produce_different_hashes(self):
        """Test that different keys produce different hashes."""
        hash1 = hash_api_key("key1")
        hash2 = hash_api_key("key2")

        assert hash1 != hash2


class TestGenerateApiKey:
    """Tests for generate_api_key function."""

    def test_generate_with_default_prefix(self):
        """Test generating key with default prefix."""
        key = generate_api_key()

        assert key.startswith("gw_")
        assert len(key) > 20

    def test_generate_with_custom_prefix(self):
        """Test generating key with custom prefix."""
        key = generate_api_key(prefix="test")

        assert key.startswith("test_")

    def test_generated_keys_are_unique(self):
        """Test that generated keys are unique."""
        keys = [generate_api_key() for _ in range(100)]
        unique_keys = set(keys)

        assert len(unique_keys) == len(keys)


class TestApiKeyRepositoryCreate:
    """Tests for creating API keys."""

    @pytest.mark.asyncio
    async def test_create_minimal(self):
        """Test creating an API key with minimal fields."""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        repo = ApiKeyRepository(mock_session)
        api_key, raw_key = await repo.create(
            application_id=1,
            name="Test Key",
        )

        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        assert raw_key.startswith("gw_")

    @pytest.mark.asyncio
    async def test_create_with_all_fields(self):
        """Test creating an API key with all fields."""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        expires_at = datetime.utcnow() + timedelta(days=30)

        repo = ApiKeyRepository(mock_session)
        api_key, raw_key = await repo.create(
            application_id=1,
            name="Production Key",
            environment=Environment.PRODUCTION,
            llm_api_key="sk-1234567890",
            expires_at=expires_at,
        )

        mock_session.add.assert_called_once()
        assert raw_key.startswith("gw_")


class TestApiKeyRepositoryGet:
    """Tests for getting API keys."""

    @pytest.mark.asyncio
    async def test_get_by_key_found(self):
        """Test getting API key by raw key when found."""
        mock_session = AsyncMock()
        mock_api_key = MagicMock(spec=ApiKey)
        mock_api_key.key_hash = hash_api_key("gw_test_key")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_api_key
        mock_session.execute.return_value = mock_result

        repo = ApiKeyRepository(mock_session)
        result = await repo.get_by_key("gw_test_key")

        assert result == mock_api_key

    @pytest.mark.asyncio
    async def test_get_by_key_not_found(self):
        """Test getting API key by raw key when not found."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = ApiKeyRepository(mock_session)
        result = await repo.get_by_key("gw_nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_found(self):
        """Test getting API key by ID when found."""
        mock_session = AsyncMock()
        mock_api_key = MagicMock(spec=ApiKey)
        mock_api_key.id = 1

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_api_key
        mock_session.execute.return_value = mock_result

        repo = ApiKeyRepository(mock_session)
        result = await repo.get_by_id(1)

        assert result == mock_api_key

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self):
        """Test getting API key by ID when not found."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = ApiKeyRepository(mock_session)
        result = await repo.get_by_id(999)

        assert result is None


class TestApiKeyRepositoryList:
    """Tests for listing API keys."""

    @pytest.mark.asyncio
    async def test_list_by_application(self):
        """Test listing API keys for an application."""
        mock_session = AsyncMock()
        mock_keys = [MagicMock(spec=ApiKey), MagicMock(spec=ApiKey)]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_keys
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = ApiKeyRepository(mock_session)
        result = await repo.list_by_application(application_id=1)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_by_application_all(self):
        """Test listing all API keys including inactive."""
        mock_session = AsyncMock()
        mock_keys = [
            MagicMock(spec=ApiKey, is_active=True),
            MagicMock(spec=ApiKey, is_active=False),
        ]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_keys
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = ApiKeyRepository(mock_session)
        result = await repo.list_by_application(application_id=1, active_only=False)

        assert len(result) == 2


class TestApiKeyRepositoryValidate:
    """Tests for API key validation."""

    @pytest.mark.asyncio
    async def test_validate_key_not_found(self):
        """Test validating non-existent key."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = ApiKeyRepository(mock_session)
        result = await repo.validate_key("gw_nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_validate_key_inactive(self):
        """Test validating inactive key."""
        mock_session = AsyncMock()
        mock_api_key = MagicMock(spec=ApiKey)
        mock_api_key.is_active = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_api_key
        mock_session.execute.return_value = mock_result

        repo = ApiKeyRepository(mock_session)
        result = await repo.validate_key("gw_inactive")

        assert result is None


class TestApiKeyRepositoryDeactivate:
    """Tests for deactivating API keys."""

    @pytest.mark.asyncio
    async def test_deactivate_found(self):
        """Test deactivating an API key when found."""
        mock_session = AsyncMock()
        mock_api_key = MagicMock(spec=ApiKey)
        mock_api_key.is_active = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_api_key
        mock_session.execute.return_value = mock_result
        mock_session.flush = AsyncMock()

        repo = ApiKeyRepository(mock_session)
        result = await repo.deactivate(id=1)

        assert result is True
        assert mock_api_key.is_active is False

    @pytest.mark.asyncio
    async def test_deactivate_not_found(self):
        """Test deactivating an API key when not found."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = ApiKeyRepository(mock_session)
        result = await repo.deactivate(id=999)

        assert result is False


class TestApiKeyRepositoryRotate:
    """Tests for rotating API keys."""

    @pytest.mark.asyncio
    async def test_rotate_not_found(self):
        """Test rotating an API key when not found."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = ApiKeyRepository(mock_session)
        result = await repo.rotate(id=999)

        assert result is None


class TestApiKeyRepositoryDelete:
    """Tests for deleting API keys."""

    @pytest.mark.asyncio
    async def test_delete_found(self):
        """Test deleting an API key when found."""
        mock_session = AsyncMock()
        mock_api_key = MagicMock(spec=ApiKey)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_api_key
        mock_session.execute.return_value = mock_result
        mock_session.delete = AsyncMock()
        mock_session.flush = AsyncMock()

        repo = ApiKeyRepository(mock_session)
        result = await repo.delete(id=1)

        assert result is True
        mock_session.delete.assert_called_once_with(mock_api_key)

    @pytest.mark.asyncio
    async def test_delete_not_found(self):
        """Test deleting an API key when not found."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = ApiKeyRepository(mock_session)
        result = await repo.delete(id=999)

        assert result is False
