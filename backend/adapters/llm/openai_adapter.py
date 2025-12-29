"""OpenAI Adapter - Implémentation native du port LLMProviderPort.

Architecture Hexagonale: Adapter natif qui implémente directement
l'interface LLMProviderPort sans dépendre du code legacy.
"""

from typing import AsyncIterator
import httpx

from backend.ports.llm_provider import LLMProviderPort
from backend.domain.models import ChatRequest, ChatResponse


class OpenAIAdapter(LLMProviderPort):
    """Adapter natif pour OpenAI API.

    Implémente directement l'interface LLMProviderPort en utilisant
    httpx pour les appels HTTP. Aucune dépendance au code legacy.
    """

    SUPPORTED_MODEL_PREFIXES = ("gpt-", "o1", "o3")
    SUPPORTED_MODELS = ("chatgpt-4o-latest",)
    DEFAULT_BASE_URL = "https://api.openai.com/v1"
    DEFAULT_TIMEOUT = 60.0

    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        """Initialise l'adapter OpenAI.

        Args:
            base_url: URL de base de l'API (défaut: https://api.openai.com/v1)
            timeout: Timeout des requêtes en secondes (défaut: 60.0)
        """
        self._base_url = base_url or self.DEFAULT_BASE_URL
        self._timeout = timeout or self.DEFAULT_TIMEOUT

    @property
    def name(self) -> str:
        return "openai"

    def supports_model(self, model: str) -> bool:
        """Vérifie si le modèle est supporté par OpenAI."""
        if model in self.SUPPORTED_MODELS:
            return True
        return any(model.startswith(prefix) for prefix in self.SUPPORTED_MODEL_PREFIXES)

    async def chat(self, request: ChatRequest, api_key: str) -> ChatResponse:
        """Envoie une requête de chat completion à OpenAI.

        Args:
            request: Requête de chat (model, messages, etc.)
            api_key: Clé API OpenAI

        Returns:
            ChatResponse avec le contenu et les tokens utilisés

        Raises:
            httpx.HTTPStatusError: Si l'API retourne une erreur
        """
        payload = self._build_payload(request, stream=False)

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                headers=self._build_headers(api_key),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        return self._parse_response(data)

    async def chat_stream(self, request: ChatRequest, api_key: str) -> AsyncIterator[str]:
        """Stream une réponse de chat completion depuis OpenAI.

        Args:
            request: Requête de chat (model, messages, etc.)
            api_key: Clé API OpenAI

        Yields:
            Chunks de la réponse au format SSE data (JSON string)

        Raises:
            httpx.HTTPStatusError: Si l'API retourne une erreur
        """
        payload = self._build_payload(request, stream=True)

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                headers=self._build_headers(api_key),
                json=payload,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        yield data

    def _build_headers(self, api_key: str) -> dict[str, str]:
        """Construit les headers HTTP."""
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(self, request: ChatRequest, stream: bool) -> dict:
        """Construit le payload de la requête.

        Args:
            request: Requête de chat
            stream: Active le streaming

        Returns:
            Payload JSON pour l'API OpenAI
        """
        payload = {
            "model": request.model,
            "messages": [{"role": msg.role, "content": msg.content} for msg in request.messages],
            "stream": stream,
        }

        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.temperature is not None:
            payload["temperature"] = request.temperature

        return payload

    def _parse_response(self, data: dict) -> ChatResponse:
        """Parse la réponse JSON de l'API.

        Args:
            data: Réponse JSON de l'API OpenAI

        Returns:
            ChatResponse domain object
        """
        choice = data["choices"][0]
        usage = data.get("usage", {})

        return ChatResponse(
            id=data["id"],
            model=data["model"],
            content=choice["message"]["content"],
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            finish_reason=choice.get("finish_reason"),
        )
