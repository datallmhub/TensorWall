"""
Ollama Provider.

Ollama exposes an OpenAI-compatible API, so we can reuse most logic.
It also has a /api/tags endpoint to list available models.
"""

from typing import AsyncIterator, Optional, List
import httpx

from backend.application.providers.base import LLMProvider, ChatRequest, ChatResponse
from backend.core.config import settings
from pydantic import BaseModel


class OllamaModelInfo(BaseModel):
    """Information about an Ollama model."""

    name: str
    size: Optional[int] = None
    digest: Optional[str] = None
    modified_at: Optional[str] = None


class OllamaProvider(LLMProvider):
    """
    Ollama provider using OpenAI-compatible API.

    Ollama runs locally and provides:
    - /api/tags - List available models
    - /v1/chat/completions - OpenAI-compatible chat API
    """

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or getattr(settings, "ollama_api_url", "http://localhost:11434")
        self._cached_models: List[str] = []

    def supports_model(self, model: str) -> bool:
        """Check if model is available in Ollama."""
        # Common Ollama model prefixes
        ollama_prefixes = [
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
        ]
        model_lower = model.lower()
        return any(model_lower.startswith(prefix) for prefix in ollama_prefixes)

    async def list_models(self) -> List[OllamaModelInfo]:
        """Fetch list of available models from Ollama."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                data = response.json()

                models = []
                for model_data in data.get("models", []):
                    models.append(
                        OllamaModelInfo(
                            name=model_data.get("name", ""),
                            size=model_data.get("size"),
                            digest=model_data.get("digest"),
                            modified_at=model_data.get("modified_at"),
                        )
                    )

                self._cached_models = [m.name for m in models]
                return models

        except Exception:
            return []

    async def is_available(self) -> bool:
        """Check if Ollama server is running."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    async def chat(self, request: ChatRequest, api_key: str = "") -> ChatResponse:
        """Send chat completion request to Ollama (OpenAI-compatible)."""

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                headers={"Content-Type": "application/json"},
                json={
                    "model": request.model,
                    "messages": [m.model_dump() for m in request.messages],
                    "max_tokens": request.max_tokens or 2048,
                    "temperature": request.temperature or 0.7,
                    "stream": False,
                },
            )

            response.raise_for_status()
            data = response.json()

            return ChatResponse(
                id=data.get("id", f"ollama-{request.model}"),
                model=data.get("model", request.model),
                content=data["choices"][0]["message"]["content"],
                input_tokens=data.get("usage", {}).get("prompt_tokens", 0),
                output_tokens=data.get("usage", {}).get("completion_tokens", 0),
                finish_reason=data["choices"][0].get("finish_reason", "stop"),
            )

    async def chat_stream(self, request: ChatRequest, api_key: str = "") -> AsyncIterator[str]:
        """Stream chat completion from Ollama."""

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/v1/chat/completions",
                headers={"Content-Type": "application/json"},
                json={
                    "model": request.model,
                    "messages": [m.model_dump() for m in request.messages],
                    "max_tokens": request.max_tokens or 2048,
                    "temperature": request.temperature or 0.7,
                    "stream": True,
                },
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        yield data


# Singleton
ollama_provider = OllamaProvider()
