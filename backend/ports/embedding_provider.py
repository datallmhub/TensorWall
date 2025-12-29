"""Embedding Provider Port - Interface abstraite pour les providers d'embedding.

Architecture Hexagonale: Port (interface) que les Adapters implémentent.
"""

from abc import ABC, abstractmethod

from backend.domain.models import EmbeddingRequest, EmbeddingResponse


class EmbeddingProviderPort(ABC):
    """Interface abstraite pour les providers d'embedding.

    Cette interface définit le contrat que tous les providers d'embedding
    doivent respecter. Les adapters concrets (OpenAI, etc.)
    implémentent cette interface.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Nom du provider."""
        pass

    @abstractmethod
    def supports_model(self, model: str) -> bool:
        """Vérifie si le provider supporte le modèle donné.

        Args:
            model: Nom du modèle (ex: "text-embedding-ada-002")

        Returns:
            True si le provider supporte ce modèle
        """
        pass

    @abstractmethod
    async def embed(self, request: EmbeddingRequest, api_key: str) -> EmbeddingResponse:
        """Génère des embeddings pour les inputs.

        Args:
            request: Requête d'embedding (model, inputs)
            api_key: Clé API du provider

        Returns:
            Réponse avec les embeddings générés
        """
        pass
