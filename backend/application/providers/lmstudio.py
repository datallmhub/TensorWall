"""
LM Studio Provider.

LM Studio exposes an OpenAI-compatible API on localhost:1234.
It also has a /v1/models endpoint to list loaded models.

Also handles models with provider=lmstudio in the database,
using their configured base_url and provider_model_id.
"""

from typing import AsyncIterator, Optional, List
import httpx

from backend.application.providers.base import LLMProvider, ChatRequest, ChatResponse
from backend.core.config import settings
from pydantic import BaseModel

# Cache for model configs from database
_model_config_cache: dict = {}


class LMStudioModelInfo(BaseModel):
    """Information about an LM Studio model."""

    id: str
    object: str = "model"
    owned_by: str = "lmstudio"


class LMStudioProvider(LLMProvider):
    """
    LM Studio provider using OpenAI-compatible API.

    LM Studio runs locally and provides:
    - /v1/models - List loaded models
    - /v1/chat/completions - OpenAI-compatible chat API
    """

    name = "lmstudio"

    # URLs to try for auto-discovery (in order)
    DEFAULT_URLS = [
        "http://host.docker.internal:11434",  # Docker -> host (common for LM Studio/Ollama)
        "http://host.docker.internal:1234",  # Docker -> host (LM Studio default)
        "http://localhost:11434",  # Direct (Ollama default)
        "http://localhost:1234",  # Direct (LM Studio default)
    ]

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or getattr(settings, "lmstudio_api_url", None)
        self._discovered_url: Optional[str] = None
        self._cached_models: List[str] = []

    def supports_model(self, model: str) -> bool:
        """Check if model is loaded in LM Studio."""
        # LM Studio can load any GGUF model, check cache
        if self._cached_models:
            return model in self._cached_models
        # Support local/* prefix for models added via admin API
        if model.startswith("local/"):
            return True
        # Support lmstudio/* prefix
        if model.startswith("lmstudio/"):
            return True
        # Common local model patterns
        return ".gguf" in model.lower() or "local-" in model.lower()

    def _is_embedding_model(self, model_id: str) -> bool:
        """Check if model is an embedding model (can't do chat)."""
        model_lower = model_id.lower()
        embedding_patterns = [
            "embed",
            "embedding",
            "bge-",
            "nomic-embed",
            "reranker",
            "e5-",
            "gte-",
            "instructor-",
        ]
        return any(pattern in model_lower for pattern in embedding_patterns)

    async def list_models(self) -> List[LMStudioModelInfo]:
        """Fetch list of chat models from LM Studio (excludes embedding models)."""
        try:
            url = await self._discover_server()
            if not url:
                return []

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{url}/v1/models")
                response.raise_for_status()
                data = response.json()

                models = []
                for model_data in data.get("data", []):
                    model_id = model_data.get("id", "")
                    # Skip embedding models
                    if self._is_embedding_model(model_id):
                        continue
                    models.append(
                        LMStudioModelInfo(
                            id=model_id,
                            object=model_data.get("object", "model"),
                            owned_by=model_data.get("owned_by", "lmstudio"),
                        )
                    )

                self._cached_models = [m.id for m in models]
                return models

        except Exception:
            return []

    async def _discover_server(self) -> Optional[str]:
        """Auto-discover the local server URL by trying known endpoints."""
        if self._discovered_url:
            return self._discovered_url

        # If explicitly configured, use that
        if self.base_url:
            return self.base_url

        # Try each URL until one works
        async with httpx.AsyncClient(timeout=3.0) as client:
            for url in self.DEFAULT_URLS:
                try:
                    response = await client.get(f"{url}/v1/models")
                    if response.status_code == 200:
                        self._discovered_url = url
                        return url
                except Exception:
                    continue
        return None

    async def is_available(self) -> bool:
        """Check if LM Studio server is running."""
        url = await self._discover_server()
        return url is not None

    async def _get_model_config(self, model_id: str) -> tuple[str, str]:
        """
        Get base_url and provider_model_id.

        Priority:
        1. Database config (if model registered)
        2. Auto-discovered server URL
        3. Strip prefix and use model name directly
        """
        if model_id in _model_config_cache:
            return _model_config_cache[model_id]

        # Try to fetch from database (async)
        try:
            from backend.db.session import get_db_context
            from backend.db.models import LLMModel
            from sqlalchemy import select

            async with get_db_context() as db:
                result = await db.execute(select(LLMModel).where(LLMModel.model_id == model_id))
                model = result.scalar_one_or_none()
                if model and model.base_url:
                    _model_config_cache[model_id] = (model.base_url, model.provider_model_id)
                    return model.base_url, model.provider_model_id
        except Exception:
            pass

        # Auto-discover server and use model_id directly
        server_url = await self._discover_server()
        if not server_url:
            server_url = self.DEFAULT_URLS[0]  # Fallback

        # Strip common prefixes to get the actual model name
        provider_model_id = model_id
        for prefix in ("local/", "lmstudio/", "ollama/"):
            if model_id.startswith(prefix):
                provider_model_id = model_id[len(prefix) :]
                break

        _model_config_cache[model_id] = (server_url, provider_model_id)
        return server_url, provider_model_id

    async def chat(self, request: ChatRequest, api_key: str = "") -> ChatResponse:
        """Send chat completion request to LM Studio (OpenAI-compatible)."""
        # Get model config (may have custom base_url)
        base_url, provider_model_id = await self._get_model_config(request.model)

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{base_url}/v1/chat/completions",
                headers={"Content-Type": "application/json"},
                json={
                    "model": provider_model_id,
                    "messages": [m.model_dump() for m in request.messages],
                    "max_tokens": request.max_tokens or 2048,
                    "temperature": request.temperature or 0.7,
                    "stream": False,
                },
            )

            response.raise_for_status()
            data = response.json()

            return ChatResponse(
                id=data.get("id", f"lmstudio-{request.model}"),
                model=data.get("model", request.model),
                content=data["choices"][0]["message"]["content"],
                input_tokens=data.get("usage", {}).get("prompt_tokens", 0),
                output_tokens=data.get("usage", {}).get("completion_tokens", 0),
                finish_reason=data["choices"][0].get("finish_reason", "stop"),
            )

    async def chat_stream(self, request: ChatRequest, api_key: str = "") -> AsyncIterator[str]:
        """Stream chat completion from LM Studio."""
        # Get model config (may have custom base_url)
        base_url, provider_model_id = await self._get_model_config(request.model)

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{base_url}/v1/chat/completions",
                headers={"Content-Type": "application/json"},
                json={
                    "model": provider_model_id,
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
lmstudio_provider = LMStudioProvider()
