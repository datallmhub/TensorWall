"""Ollama Adapter - Implémentation du port LLMProviderPort pour Ollama.

Architecture Hexagonale: Adapter qui implémente l'interface LLMProviderPort
pour les modèles locaux via Ollama (OpenAI-compatible API).
"""

from typing import AsyncIterator
import httpx

from backend.ports.llm_provider import LLMProviderPort
from backend.domain.models import ChatRequest, ChatResponse
from backend.core.config import settings


class OllamaAdapter(LLMProviderPort):
    """Adapter pour Ollama (OpenAI-compatible API).

    Supporte les modèles locaux comme Llama, Mistral, Qwen, etc.
    """

    SUPPORTED_MODEL_PREFIXES = (
        "llama",
        "mistral",
        "mixtral",
        "codellama",
        "phi",
        "gemma",
        "qwen",
        "deepseek",
        "starcoder",
        "wizard",
        "neural-chat",
        "openchat",
        "orca",
        "vicuna",
        "zephyr",
        "dolphin",
        "nous-hermes",
        "solar",
        "yi",
        "falcon",
        "tinyllama",
        "granite",
        "codegemma",
        "minicpm",
    )
    DEFAULT_BASE_URL = "http://localhost:11434"
    DEFAULT_TIMEOUT = 120.0

    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        """Initialise l'adapter Ollama.

        Args:
            base_url: URL de base de l'API Ollama (défaut: http://localhost:11434)
            timeout: Timeout des requêtes en secondes (défaut: 120.0)
        """
        self._base_url = base_url or getattr(settings, "ollama_api_url", self.DEFAULT_BASE_URL)
        self._timeout = timeout or self.DEFAULT_TIMEOUT

    @property
    def name(self) -> str:
        return "ollama"

    def supports_model(self, model: str) -> bool:
        """Vérifie si le modèle est supporté par Ollama."""
        model_lower = model.lower()
        # Check prefixes
        for prefix in self.SUPPORTED_MODEL_PREFIXES:
            if model_lower.startswith(prefix):
                return True
        # Check if it contains a slash (like qwen/qwen2.5-vl-7b)
        if "/" in model:
            model_name = model.split("/")[-1].lower()
            for prefix in self.SUPPORTED_MODEL_PREFIXES:
                if model_name.startswith(prefix):
                    return True
            # Also check the org name
            org_name = model.split("/")[0].lower()
            for prefix in self.SUPPORTED_MODEL_PREFIXES:
                if org_name.startswith(prefix):
                    return True
        return False

    async def chat(self, request: ChatRequest, api_key: str = "") -> ChatResponse:
        """Envoie une requête de chat completion à Ollama.

        Args:
            request: Requête de chat (model, messages, etc.)
            api_key: Non utilisé pour Ollama (modèles locaux)

        Returns:
            ChatResponse avec le contenu et les tokens utilisés
        """
        payload = self._build_payload(request, stream=False)

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/v1/chat/completions",
                headers={"Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        return self._parse_response(data)

    async def chat_stream(self, request: ChatRequest, api_key: str = "") -> AsyncIterator[str]:
        """Stream une réponse de chat completion depuis Ollama.

        Args:
            request: Requête de chat (model, messages, etc.)
            api_key: Non utilisé pour Ollama

        Yields:
            Chunks de la réponse au format SSE data (JSON string)
        """
        payload = self._build_payload(request, stream=True)

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/v1/chat/completions",
                headers={"Content-Type": "application/json"},
                json=payload,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        yield data

    def _build_payload(self, request: ChatRequest, stream: bool) -> dict:
        """Construit le payload de la requête."""
        # Strip provider prefix if present (lmstudio/, ollama/)
        model = request.model
        for prefix in ("lmstudio/", "ollama/"):
            if model.startswith(prefix):
                model = model[len(prefix) :]
                break

        payload = {
            "model": model,
            "messages": [{"role": msg.role, "content": msg.content} for msg in request.messages],
            "stream": stream,
        }

        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.temperature is not None:
            payload["temperature"] = request.temperature

        return payload

    def _parse_response(self, data: dict) -> ChatResponse:
        """Parse la réponse JSON de l'API."""
        choice = data["choices"][0]
        usage = data.get("usage", {})

        return ChatResponse(
            id=data.get("id", f"ollama-{data.get('model', 'unknown')}"),
            model=data.get("model", "unknown"),
            content=choice["message"]["content"],
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            finish_reason=choice.get("finish_reason", "stop"),
        )
