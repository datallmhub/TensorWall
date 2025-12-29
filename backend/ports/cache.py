"""Cache Port - Interface abstraite pour le cache.

Architecture Hexagonale: Port (interface) pour le cache.
"""

from abc import ABC, abstractmethod
from typing import Any


class CachePort(ABC):
    """Interface abstraite pour le cache.

    Cette interface définit le contrat pour les opérations de cache.
    Les adapters (Redis, In-Memory, etc.) implémentent cette interface.
    """

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """Récupère une valeur du cache.

        Args:
            key: Clé de cache

        Returns:
            La valeur ou None si non trouvée
        """
        pass

    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int | None = None,
    ) -> bool:
        """Stocke une valeur dans le cache.

        Args:
            key: Clé de cache
            value: Valeur à stocker
            ttl_seconds: Durée de vie en secondes (None = pas d'expiration)

        Returns:
            True si stocké avec succès
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Supprime une valeur du cache.

        Args:
            key: Clé de cache

        Returns:
            True si supprimée, False si non trouvée
        """
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Vérifie si une clé existe dans le cache.

        Args:
            key: Clé de cache

        Returns:
            True si la clé existe
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def expire(self, key: str, ttl_seconds: int) -> bool:
        """Définit un TTL sur une clé existante.

        Args:
            key: Clé de cache
            ttl_seconds: Durée de vie en secondes

        Returns:
            True si le TTL a été défini
        """
        pass
