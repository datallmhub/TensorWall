"""Anthropic Adapter - Implémentation native du port LLMProviderPort.

Architecture Hexagonale: Adapter natif qui implémente directement
l'interface LLMProviderPort sans dépendre du code legacy.
"""

from typing import AsyncIterator
import httpx
import json

from backend.ports.llm_provider import LLMProviderPort
from backend.domain.models import ChatRequest, ChatResponse, ChatMessage


class AnthropicAdapter(LLMProviderPort):
    """Adapter natif pour Anthropic Claude API.

    Implémente directement l'interface LLMProviderPort en utilisant
    httpx pour les appels HTTP. Aucune dépendance au code legacy.

    Note: Convertit automatiquement le format OpenAI vers le format Anthropic.
    """

    SUPPORTED_MODEL_PREFIX = "claude-"
    DEFAULT_BASE_URL = "https://api.anthropic.com/v1"
    DEFAULT_TIMEOUT = 60.0
    DEFAULT_MAX_TOKENS = 4096
    ANTHROPIC_VERSION = "2023-06-01"

    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        """Initialise l'adapter Anthropic.

        Args:
            base_url: URL de base de l'API (défaut: https://api.anthropic.com/v1)
            timeout: Timeout des requêtes en secondes (défaut: 60.0)
        """
        self._base_url = base_url or self.DEFAULT_BASE_URL
        self._timeout = timeout or self.DEFAULT_TIMEOUT

    @property
    def name(self) -> str:
        return "anthropic"

    def supports_model(self, model: str) -> bool:
        """Vérifie si le modèle est supporté par Anthropic."""
        return model.startswith(self.SUPPORTED_MODEL_PREFIX)

    async def chat(self, request: ChatRequest, api_key: str) -> ChatResponse:
        """Envoie une requête de chat completion à Anthropic.

        Args:
            request: Requête de chat (model, messages, etc.)
            api_key: Clé API Anthropic

        Returns:
            ChatResponse avec le contenu et les tokens utilisés

        Raises:
            httpx.HTTPStatusError: Si l'API retourne une erreur
        """
        system, messages = self._convert_messages(request.messages)
        payload = self._build_payload(request, system, messages, stream=False)

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/messages",
                headers=self._build_headers(api_key),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        return self._parse_response(data)

    async def chat_stream(
        self, request: ChatRequest, api_key: str
    ) -> AsyncIterator[str]:
        """Stream une réponse de chat completion depuis Anthropic.

        Convertit le format de streaming Anthropic vers le format OpenAI
        pour compatibilité avec les clients existants.

        Args:
            request: Requête de chat (model, messages, etc.)
            api_key: Clé API Anthropic

        Yields:
            Chunks de la réponse au format OpenAI SSE data (JSON string)

        Raises:
            httpx.HTTPStatusError: Si l'API retourne une erreur
        """
        system, messages = self._convert_messages(request.messages)
        payload = self._build_payload(request, system, messages, stream=True)

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/messages",
                headers=self._build_headers(api_key),
                json=payload,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        try:
                            event = json.loads(data)
                            # Convertir l'événement Anthropic vers le format OpenAI
                            openai_chunk = self._convert_stream_event(event)
                            if openai_chunk is None:
                                # message_stop event
                                break
                            if openai_chunk:
                                yield json.dumps(openai_chunk)
                        except json.JSONDecodeError:
                            continue

    def _build_headers(self, api_key: str) -> dict[str, str]:
        """Construit les headers HTTP pour Anthropic."""
        return {
            "x-api-key": api_key,
            "anthropic-version": self.ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        }

    def _convert_messages(
        self, messages: list[ChatMessage]
    ) -> tuple[str | None, list[dict]]:
        """Convertit les messages du format OpenAI vers le format Anthropic.

        Anthropic gère le message système séparément des autres messages.

        Args:
            messages: Liste de messages au format OpenAI

        Returns:
            Tuple (system_message, anthropic_messages)
        """
        system = None
        anthropic_messages = []

        for msg in messages:
            if msg.role == "system":
                system = msg.content
            else:
                anthropic_messages.append(
                    {
                        "role": msg.role,
                        "content": msg.content,
                    }
                )

        return system, anthropic_messages

    def _build_payload(
        self,
        request: ChatRequest,
        system: str | None,
        messages: list[dict],
        stream: bool,
    ) -> dict:
        """Construit le payload de la requête pour Anthropic.

        Args:
            request: Requête de chat
            system: Message système (optionnel)
            messages: Messages convertis au format Anthropic
            stream: Active le streaming

        Returns:
            Payload JSON pour l'API Anthropic
        """
        payload = {
            "model": request.model,
            "messages": messages,
            "max_tokens": request.max_tokens or self.DEFAULT_MAX_TOKENS,
        }

        if stream:
            payload["stream"] = True
        if system:
            payload["system"] = system
        if request.temperature is not None:
            payload["temperature"] = request.temperature

        return payload

    def _parse_response(self, data: dict) -> ChatResponse:
        """Parse la réponse JSON de l'API Anthropic.

        Args:
            data: Réponse JSON de l'API Anthropic

        Returns:
            ChatResponse domain object
        """
        # Extraire le contenu textuel des blocs
        content = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                content += block.get("text", "")

        return ChatResponse(
            id=data["id"],
            model=data["model"],
            content=content,
            input_tokens=data["usage"]["input_tokens"],
            output_tokens=data["usage"]["output_tokens"],
            finish_reason=data.get("stop_reason") or "stop",
        )

    def _convert_stream_event(self, event: dict) -> dict | None:
        """Convertit un événement de streaming Anthropic vers le format OpenAI.

        Args:
            event: Événement SSE Anthropic

        Returns:
            Chunk au format OpenAI, ou None si message_stop
        """
        event_type = event.get("type")

        if event_type == "content_block_delta":
            delta = event.get("delta", {})
            if delta.get("type") == "text_delta":
                return {
                    "choices": [
                        {
                            "delta": {"content": delta.get("text", "")},
                            "index": 0,
                        }
                    ]
                }
        elif event_type == "message_stop":
            return None

        # Ignorer les autres types d'événements
        return {}
