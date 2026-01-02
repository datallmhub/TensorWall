"""
Groq Provider

Ultra-fast inference for open-source models:
- Llama 3 (8B, 70B)
- Mixtral 8x7B
- Gemma 7B

Features:
- OpenAI-compatible API
- Sub-second latency
- High throughput
"""

from typing import AsyncIterator
import httpx

from backend.application.providers.base import LLMProvider, ChatRequest, ChatResponse


class GroqProvider(LLMProvider):
    """Groq API provider for ultra-fast LLM inference."""

    name = "groq"

    # Supported models
    SUPPORTED_MODELS = {
        # Llama 3
        "llama3-8b-8192",
        "llama3-70b-8192",
        "llama-3.1-8b-instant",
        "llama-3.1-70b-versatile",
        "llama-3.2-1b-preview",
        "llama-3.2-3b-preview",
        "llama-3.2-11b-vision-preview",
        "llama-3.2-90b-vision-preview",
        "llama-3.3-70b-versatile",
        # Mixtral
        "mixtral-8x7b-32768",
        # Gemma
        "gemma-7b-it",
        "gemma2-9b-it",
        # Whisper (for audio, not chat)
        "whisper-large-v3",
    }

    def __init__(self, base_url: str = "https://api.groq.com/openai/v1"):
        """Initialize Groq provider."""
        self.base_url = base_url

    def supports_model(self, model: str) -> bool:
        """Check if model is supported by Groq."""
        return (
            model in self.SUPPORTED_MODELS
            or model.startswith("llama")
            or model.startswith("mixtral")
            or model.startswith("gemma")
        )

    async def chat(self, request: ChatRequest, api_key: str) -> ChatResponse:
        """Send chat completion request to Groq."""

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": request.model,
                    "messages": [m.model_dump() for m in request.messages],
                    "max_tokens": request.max_tokens or 1024,
                    "temperature": request.temperature or 0.7,
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
        """Stream chat completion from Groq."""

        async with httpx.AsyncClient(timeout=30.0) as client:
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
                    "max_tokens": request.max_tokens or 1024,
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


# Default singleton
groq_provider = GroqProvider()
