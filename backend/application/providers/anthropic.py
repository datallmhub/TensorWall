from typing import AsyncIterator, Optional
import httpx
import json

from backend.application.providers.base import LLMProvider, ChatRequest, ChatResponse
from backend.core.config import settings


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API provider."""

    name = "anthropic"

    def __init__(self):
        self.base_url = settings.anthropic_api_url

    def supports_model(self, model: str) -> bool:
        """Check if model is supported by Anthropic provider (pattern matching only)."""
        return model.startswith("claude-")

    def _convert_messages(self, messages: list) -> tuple[Optional[str], list]:
        """Convert OpenAI format to Anthropic format."""
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

    async def chat(self, request: ChatRequest, api_key: str) -> ChatResponse:
        """Send chat completion request to Anthropic."""

        system, messages = self._convert_messages(request.messages)

        body = {
            "model": request.model,
            "messages": messages,
            "max_tokens": request.max_tokens or 4096,
        }
        if system:
            body["system"] = system
        if request.temperature is not None:
            body["temperature"] = request.temperature

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json=body,
            )

            response.raise_for_status()
            data = response.json()

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
                finish_reason=data["stop_reason"] or "stop",
            )

    async def chat_stream(
        self, request: ChatRequest, api_key: str
    ) -> AsyncIterator[str]:
        """Stream chat completion from Anthropic (converted to OpenAI format)."""

        system, messages = self._convert_messages(request.messages)

        body = {
            "model": request.model,
            "messages": messages,
            "max_tokens": request.max_tokens or 4096,
            "stream": True,
        }
        if system:
            body["system"] = system
        if request.temperature is not None:
            body["temperature"] = request.temperature

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json=body,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        try:
                            event = json.loads(data)
                            # Convert Anthropic event to OpenAI format
                            if event.get("type") == "content_block_delta":
                                delta = event.get("delta", {})
                                if delta.get("type") == "text_delta":
                                    openai_chunk = {
                                        "choices": [
                                            {
                                                "delta": {
                                                    "content": delta.get("text", "")
                                                },
                                                "index": 0,
                                            }
                                        ]
                                    }
                                    yield json.dumps(openai_chunk)
                            elif event.get("type") == "message_stop":
                                break
                        except json.JSONDecodeError:
                            continue


# Singleton
anthropic_provider = AnthropicProvider()
