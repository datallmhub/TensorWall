"""Mock Adapter - Implémentation native pour les tests.

Architecture Hexagonale: Adapter natif qui implémente directement
l'interface LLMProviderPort sans dépendre du code legacy.
Utile pour les tests unitaires et d'intégration.
"""

from typing import AsyncIterator
import asyncio
import json
import uuid

from backend.ports.llm_provider import LLMProviderPort
from backend.domain.models import ChatRequest, ChatResponse


class MockAdapter(LLMProviderPort):
    """Adapter mock natif pour les tests.

    Simule les réponses LLM sans appeler d'API externe.
    Aucune dépendance au code legacy.
    """

    SUPPORTED_MODEL_PREFIXES = ("mock-",)
    SUPPORTED_MODELS = ("test-model",)
    DEFAULT_LATENCY = 0.1  # Simulated latency in seconds
    STREAM_DELAY = 0.05  # Delay between stream chunks

    def __init__(
        self,
        latency: float | None = None,
        stream_delay: float | None = None,
        fixed_response: str | None = None,
    ):
        """Initialise l'adapter Mock.

        Args:
            latency: Latence simulée en secondes (défaut: 0.1)
            stream_delay: Délai entre les chunks de streaming (défaut: 0.05)
            fixed_response: Réponse fixe à retourner (optionnel)
        """
        self._latency = latency if latency is not None else self.DEFAULT_LATENCY
        self._stream_delay = stream_delay if stream_delay is not None else self.STREAM_DELAY
        self._fixed_response = fixed_response

    @property
    def name(self) -> str:
        return "mock"

    def supports_model(self, model: str) -> bool:
        """Vérifie si le modèle est supporté (modèles mock uniquement)."""
        if model in self.SUPPORTED_MODELS:
            return True
        return any(model.startswith(prefix) for prefix in self.SUPPORTED_MODEL_PREFIXES)

    async def chat(self, request: ChatRequest, api_key: str) -> ChatResponse:
        """Retourne une réponse mock.

        Args:
            request: Requête de chat (model, messages, etc.)
            api_key: Clé API (ignorée pour le mock)

        Returns:
            ChatResponse avec une réponse simulée
        """
        # Simuler une latence réseau
        if self._latency > 0:
            await asyncio.sleep(self._latency)

        # Générer la réponse
        content = self._generate_response(request)

        # Estimer les tokens (approximation)
        input_tokens = self._estimate_tokens(request.messages)
        output_tokens = self._estimate_tokens_from_text(content)

        return ChatResponse(
            id=f"mock-{uuid.uuid4().hex[:8]}",
            model=request.model,
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            finish_reason="stop",
        )

    async def chat_stream(self, request: ChatRequest, api_key: str) -> AsyncIterator[str]:
        """Stream une réponse mock mot par mot.

        Args:
            request: Requête de chat (model, messages, etc.)
            api_key: Clé API (ignorée pour le mock)

        Yields:
            Chunks de la réponse au format OpenAI SSE data (JSON string)
        """
        # Obtenir la réponse complète d'abord
        response = await self.chat(request, api_key)

        # Streamer mot par mot
        words = response.content.split()
        for word in words:
            if self._stream_delay > 0:
                await asyncio.sleep(self._stream_delay)
            chunk = {
                "choices": [
                    {
                        "delta": {"content": f"{word} "},
                        "index": 0,
                    }
                ]
            }
            yield json.dumps(chunk)

        # Envoyer le chunk final
        final_chunk = {
            "choices": [
                {
                    "delta": {},
                    "finish_reason": "stop",
                    "index": 0,
                }
            ]
        }
        yield json.dumps(final_chunk)

    def _generate_response(self, request: ChatRequest) -> str:
        """Génère une réponse mock basée sur le message utilisateur.

        Args:
            request: Requête de chat

        Returns:
            Contenu de la réponse simulée
        """
        if self._fixed_response:
            return self._fixed_response

        # Trouver le dernier message utilisateur
        user_message = ""
        for msg in request.messages:
            if msg.role == "user":
                user_message = msg.content

        # Générer une réponse basée sur le message
        if len(user_message) > 50:
            return f"This is a mock response to: '{user_message[:50]}...'"
        return f"This is a mock response to: '{user_message}'"

    def _estimate_tokens(self, messages: list) -> int:
        """Estime le nombre de tokens des messages.

        Args:
            messages: Liste de messages

        Returns:
            Nombre estimé de tokens
        """
        total_words = sum(len(msg.content.split()) for msg in messages)
        return int(total_words * 1.3)  # Approximation: ~1.3 tokens par mot

    def _estimate_tokens_from_text(self, text: str) -> int:
        """Estime le nombre de tokens d'un texte.

        Args:
            text: Texte à analyser

        Returns:
            Nombre estimé de tokens
        """
        return int(len(text.split()) * 1.3)
