"""LLM Provider Port - Interface abstraite pour les providers LLM.

Architecture Hexagonale: Port (interface) que les Adapters implémentent.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator

from backend.domain.models import ChatRequest, ChatResponse


class LLMProviderPort(ABC):
    """Interface abstraite pour les providers LLM.

    Cette interface définit le contrat que tous les providers LLM
    doivent respecter. Les adapters concrets (OpenAI, Anthropic, etc.)
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
            model: Nom du modèle (ex: "gpt-4", "claude-3-opus")

        Returns:
            True si le provider supporte ce modèle
        """
        pass

    @abstractmethod
    async def chat(self, request: ChatRequest, api_key: str) -> ChatResponse:
        """Envoie une requête de chat completion.

        Args:
            request: Requête de chat (model, messages, etc.)
            api_key: Clé API du provider

        Returns:
            Réponse du chat avec tokens utilisés
        """
        pass

    @abstractmethod
    async def chat_stream(
        self, request: ChatRequest, api_key: str
    ) -> AsyncIterator[str]:
        """Envoie une requête de chat en streaming.

        Args:
            request: Requête de chat (model, messages, etc.)
            api_key: Clé API du provider

        Yields:
            Chunks de la réponse (format SSE data)
        """
        pass
