from typing import AsyncIterator
import httpx

from backend.application.providers.base import LLMProvider, ChatRequest, ChatResponse
from backend.core.config import settings


class OpenAIProvider(LLMProvider):
    """OpenAI API provider."""

    name = "openai"

    def __init__(self):
        self.base_url = settings.openai_api_url

    def supports_model(self, model: str) -> bool:
        """Check if model is supported by OpenAI provider (pattern matching only)."""
        return (
            model.startswith("gpt-")
            or model.startswith("o1")
            or model.startswith("o3")
            or model == "chatgpt-4o-latest"
        )

    async def chat(self, request: ChatRequest, api_key: str) -> ChatResponse:
        """Send chat completion request to OpenAI."""

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
        """Stream chat completion from OpenAI."""

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


# Singleton
openai_provider = OpenAIProvider()
