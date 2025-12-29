"""Tests unitaires pour les adapters de cache.

Ces tests vérifient que les adapters de cache (Redis, InMemory)
implémentent correctement l'interface CachePort.
"""

import pytest
import time

from backend.adapters.redis import InMemoryCacheAdapter
from backend.ports.cache import CachePort


class TestInMemoryCacheAdapter:
    """Tests pour l'adapter InMemory (utilisé pour les tests)."""

    def test_implements_port(self):
        """Vérifie que l'adapter implémente le port."""
        adapter = InMemoryCacheAdapter()
        assert isinstance(adapter, CachePort)

    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self):
        """Vérifie que get retourne None pour une clé inexistante."""
        adapter = InMemoryCacheAdapter()

        result = await adapter.get("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_set_and_get(self):
        """Vérifie le stockage et la récupération."""
        adapter = InMemoryCacheAdapter()

        await adapter.set("key1", {"value": "test"})
        result = await adapter.get("key1")

        assert result == {"value": "test"}

    @pytest.mark.asyncio
    async def test_set_with_ttl(self):
        """Vérifie l'expiration avec TTL."""
        adapter = InMemoryCacheAdapter()

        # Set avec TTL très court
        await adapter.set("key1", "value", ttl_seconds=1)

        # Devrait exister immédiatement
        assert await adapter.get("key1") == "value"

        # Attendre l'expiration
        time.sleep(1.1)

        # Devrait être expiré
        assert await adapter.get("key1") is None

    @pytest.mark.asyncio
    async def test_delete_existing_key(self):
        """Vérifie la suppression d'une clé existante."""
        adapter = InMemoryCacheAdapter()
        await adapter.set("key1", "value")

        result = await adapter.delete("key1")

        assert result is True
        assert await adapter.get("key1") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_key(self):
        """Vérifie la suppression d'une clé inexistante."""
        adapter = InMemoryCacheAdapter()

        result = await adapter.delete("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_exists_true(self):
        """Vérifie exists pour une clé existante."""
        adapter = InMemoryCacheAdapter()
        await adapter.set("key1", "value")

        assert await adapter.exists("key1") is True

    @pytest.mark.asyncio
    async def test_exists_false(self):
        """Vérifie exists pour une clé inexistante."""
        adapter = InMemoryCacheAdapter()

        assert await adapter.exists("nonexistent") is False

    @pytest.mark.asyncio
    async def test_exists_expired(self):
        """Vérifie exists pour une clé expirée."""
        adapter = InMemoryCacheAdapter()
        await adapter.set("key1", "value", ttl_seconds=1)

        time.sleep(1.1)

        assert await adapter.exists("key1") is False

    @pytest.mark.asyncio
    async def test_increment_new_key(self):
        """Vérifie l'incrémentation d'une nouvelle clé."""
        adapter = InMemoryCacheAdapter()

        result = await adapter.increment("counter", 5)

        assert result == 5

    @pytest.mark.asyncio
    async def test_increment_existing_key(self):
        """Vérifie l'incrémentation d'une clé existante."""
        adapter = InMemoryCacheAdapter()
        await adapter.set("counter", 10)

        result = await adapter.increment("counter", 5)

        assert result == 15

    @pytest.mark.asyncio
    async def test_increment_default_amount(self):
        """Vérifie l'incrémentation par défaut (1)."""
        adapter = InMemoryCacheAdapter()
        await adapter.set("counter", 0)

        result = await adapter.increment("counter")

        assert result == 1

    @pytest.mark.asyncio
    async def test_expire_existing_key(self):
        """Vérifie la définition de TTL sur une clé existante."""
        adapter = InMemoryCacheAdapter()
        await adapter.set("key1", "value")

        result = await adapter.expire("key1", 1)

        assert result is True

        # Attendre l'expiration
        time.sleep(1.1)
        assert await adapter.get("key1") is None

    @pytest.mark.asyncio
    async def test_expire_nonexistent_key(self):
        """Vérifie expire sur une clé inexistante."""
        adapter = InMemoryCacheAdapter()

        result = await adapter.expire("nonexistent", 60)

        assert result is False

    @pytest.mark.asyncio
    async def test_clear(self):
        """Vérifie le vidage du cache."""
        adapter = InMemoryCacheAdapter()
        await adapter.set("key1", "value1")
        await adapter.set("key2", "value2")

        adapter.clear()

        assert await adapter.get("key1") is None
        assert await adapter.get("key2") is None

    @pytest.mark.asyncio
    async def test_set_various_types(self):
        """Vérifie le stockage de différents types."""
        adapter = InMemoryCacheAdapter()

        # String
        await adapter.set("str_key", "string value")
        assert await adapter.get("str_key") == "string value"

        # Integer
        await adapter.set("int_key", 42)
        assert await adapter.get("int_key") == 42

        # List
        await adapter.set("list_key", [1, 2, 3])
        assert await adapter.get("list_key") == [1, 2, 3]

        # Dict
        await adapter.set("dict_key", {"nested": {"value": True}})
        assert await adapter.get("dict_key") == {"nested": {"value": True}}

        # None
        await adapter.set("none_key", None)
        # Note: None est différent de "clé inexistante"
        assert await adapter.exists("none_key") is True
