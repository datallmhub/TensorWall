"""
Mistral AI Provider

Supports Mistral's models:
- Mistral 7B, 8x7B (Mixtral)
- Mistral Small, Medium, Large
- Mistral Nemo
- Codestral (code-focused)

Features:
- OpenAI-compatible API
- Function calling support
- JSON mode
"""

from typing import AsyncIterator
import httpx

from backend.application.providers.base import LLMProvider, ChatRequest, ChatResponse


class MistralProvider(LLMProvider):
    """Mistral AI provider."""

    name = "mistral"

    # Supported models
    SUPPORTED_MODELS = {
        # Production models
        "mistral-tiny",
        "mistral-small",
        "mistral-small-latest",
        "mistral-medium",
        "mistral-medium-latest",
        "mistral-large",
        "mistral-large-latest",
        # Specific versions
        "mistral-7b",
        "mixtral-8x7b",
        "mixtral-8x22b",
        # Specialized
        "mistral-nemo",
        "codestral-latest",
        "codestral-mamba-latest",
        # Open models
        "open-mistral-7b",
        "open-mixtral-8x7b",
        "open-mixtral-8x22b",
        "open-mistral-nemo",
        "open-codestral-mamba",
        # Pixtral (vision)
        "pixtral-12b-2409",
        "pixtral-large-latest",
    }

    def __init__(self, base_url: str = "https://api.mistral.ai/v1"):
        """Initialize Mistral provider."""
        self.base_url = base_url

    def supports_model(self, model: str) -> bool:
        """Check if model is supported by Mistral."""
        return (
            model in self.SUPPORTED_MODELS
            or model.startswith("mistral")
            or model.startswith("mixtral")
            or model.startswith("codestral")
            or model.startswith("pixtral")
            or model.startswith("open-mistral")
            or model.startswith("open-mixtral")
        )

    async def chat(self, request: ChatRequest, api_key: str) -> ChatResponse:
        """Send chat completion request to Mistral AI."""

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": request.model,
                    "messages": [m.model_dump() for m in request.messages],
                    "max_tokens": request.max_tokens,
                    "temperature": request.temperature,
                    "stream": False,
                },
            )

            response.raise_for_status()
            data = response.json()

            return ChatResponse(
                id=data["id"],
                model=data["model"],
                content=data["choices"][0]["message"]["content"],
                input_tokens=data["usage"]["prompt_tokens"],
                output_tokens=data["usage"]["completion_tokens"],
                finish_reason=data["choices"][0]["finish_reason"],
            )

    async def chat_stream(self, request: ChatRequest, api_key: str) -> AsyncIterator[str]:
        """Stream chat completion from Mistral AI."""

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": request.model,
                    "messages": [m.model_dump() for m in request.messages],
                    "max_tokens": request.max_tokens,
                    "temperature": request.temperature,
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


# Default singleton
mistral_provider = MistralProvider()
