"""Redis Cache Adapter - Implémentation native Redis.

Architecture Hexagonale: Adapter natif qui implémente directement
l'interface CachePort en utilisant redis.asyncio.
"""

import json
from typing import Any

import redis.asyncio as redis

from backend.ports.cache import CachePort
from backend.core.config import settings


class RedisCacheAdapter(CachePort):
    """Adapter natif pour le cache Redis.

    Implémente directement l'interface CachePort en utilisant
    redis.asyncio pour les opérations de cache.
    Aucune dépendance au code legacy (cache/).
    """

    def __init__(
        self, redis_client: redis.Redis | None = None, redis_url: str | None = None
    ):
        """Initialise l'adapter.

        Args:
            redis_client: Client Redis optionnel. Si non fourni,
                         une nouvelle connexion sera créée.
            redis_url: URL Redis optionnelle (utilisée si redis_client non fourni)
        """
        self._redis = redis_client
        self._redis_url = redis_url or settings.redis_url
        self._initialized = redis_client is not None

    async def _ensure_connected(self) -> redis.Redis:
        """S'assure que la connexion Redis est établie.

        Returns:
            Client Redis connecté
        """
        if self._redis is None:
            self._redis = redis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            self._initialized = True
        return self._redis

    async def close(self) -> None:
        """Ferme la connexion Redis."""
        if self._redis and self._initialized:
            await self._redis.close()
            self._redis = None
            self._initialized = False

    async def get(self, key: str) -> Any | None:
        """Récupère une valeur du cache.

        Args:
            key: Clé de cache

        Returns:
            La valeur désérialisée ou None si non trouvée
        """
        client = await self._ensure_connected()
        data = await client.get(key)

        if data is None:
            return None

        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            # Retourner la valeur brute si ce n'est pas du JSON
            return data

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int | None = None,
    ) -> bool:
        """Stocke une valeur dans le cache.

        Args:
            key: Clé de cache
            value: Valeur à stocker (sera sérialisée en JSON)
            ttl_seconds: Durée de vie en secondes (None = pas d'expiration)

        Returns:
            True si stocké avec succès
        """
        client = await self._ensure_connected()

        try:
            serialized = json.dumps(value)

            if ttl_seconds:
                await client.setex(key, ttl_seconds, serialized)
            else:
                await client.set(key, serialized)

            return True
        except Exception:
            return False

    async def delete(self, key: str) -> bool:
        """Supprime une valeur du cache.

        Args:
            key: Clé de cache

        Returns:
            True si supprimée, False si non trouvée
        """
        client = await self._ensure_connected()

        try:
            result = await client.delete(key)
            return result > 0
        except Exception:
            return False

    async def exists(self, key: str) -> bool:
        """Vérifie si une clé existe dans le cache.

        Args:
            key: Clé de cache

        Returns:
            True si la clé existe
        """
        client = await self._ensure_connected()
        return await client.exists(key) > 0

    async def increment(
        self,
        key: str,
        amount: int = 1,
    ) -> int:
        """Incrémente une valeur numérique.

        Args:
            key: Clé de cache
            amount: Montant à incrémenter

        Returns:
            Nouvelle valeur après incrémentation
        """
        client = await self._ensure_connected()
        result = await client.incrby(key, amount)
        return int(result)

    async def expire(self, key: str, ttl_seconds: int) -> bool:
        """Définit un TTL sur une clé existante.

        Args:
            key: Clé de cache
            ttl_seconds: Durée de vie en secondes

        Returns:
            True si le TTL a été défini
        """
        client = await self._ensure_connected()

        try:
            result = await client.expire(key, ttl_seconds)
            return bool(result)
        except Exception:
            return False


class InMemoryCacheAdapter(CachePort):
    """Adapter in-memory pour les tests.

    Implémente l'interface CachePort sans Redis.
    Utile pour les tests unitaires.
    """

    def __init__(self):
        """Initialise le cache in-memory."""
        self._store: dict[str, tuple[Any, float | None]] = {}
        import time

        self._time = time

    async def get(self, key: str) -> Any | None:
        """Récupère une valeur du cache."""
        if key not in self._store:
            return None

        value, expires_at = self._store[key]

        # Vérifier l'expiration
        if expires_at is not None and self._time.time() > expires_at:
            del self._store[key]
            return None

        return value

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int | None = None,
    ) -> bool:
        """Stocke une valeur dans le cache."""
        expires_at = None
        if ttl_seconds:
            expires_at = self._time.time() + ttl_seconds

        self._store[key] = (value, expires_at)
        return True

    async def delete(self, key: str) -> bool:
        """Supprime une valeur du cache."""
        if key in self._store:
            del self._store[key]
            return True
        return False

    async def exists(self, key: str) -> bool:
        """Vérifie si une clé existe dans le cache."""
        if key not in self._store:
            return False

        value, expires_at = self._store[key]
        if expires_at is not None and self._time.time() > expires_at:
            del self._store[key]
            return False

        return True

    async def increment(
        self,
        key: str,
        amount: int = 1,
    ) -> int:
        """Incrémente une valeur numérique."""
        current = await self.get(key)

        if current is None:
            new_value = amount
        else:
            new_value = int(current) + amount

        await self.set(key, new_value)
        return new_value

    async def expire(self, key: str, ttl_seconds: int) -> bool:
        """Définit un TTL sur une clé existante."""
        if key not in self._store:
            return False

        value, _ = self._store[key]
        expires_at = self._time.time() + ttl_seconds
        self._store[key] = (value, expires_at)
        return True

    def clear(self) -> None:
        """Vide le cache (utile pour les tests)."""
        self._store.clear()


async def create_redis_cache_adapter(redis_url: str | None = None) -> RedisCacheAdapter:
    """Factory pour créer un RedisCacheAdapter.

    Args:
        redis_url: URL Redis optionnelle (utilise settings si non fourni)

    Returns:
        Instance de RedisCacheAdapter configurée
    """
    return RedisCacheAdapter(redis_url=redis_url)
