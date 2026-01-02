"""Mock LLM Provider for testing without real API keys."""

from backend.application.providers.base import LLMProvider, ChatRequest, ChatResponse
from typing import AsyncIterator
import uuid
import asyncio


class MockProvider(LLMProvider):
    """Mock provider for testing the gateway without real LLM API calls."""

    @property
    def name(self) -> str:
        return "mock"

    def supports_model(self, model: str) -> bool:
        return model.startswith("mock-") or model == "test-model"

    async def chat(self, request: ChatRequest, api_key: str) -> ChatResponse:
        """Return a mock response."""
        # Simulate some latency
        await asyncio.sleep(0.1)

        # Generate mock response based on input
        user_message = ""
        for msg in request.messages:
            if msg.role == "user":
                user_message = msg.content
                break

        mock_content = (
            f"This is a mock response to: '{user_message[:50]}...'"
            if len(user_message) > 50
            else f"This is a mock response to: '{user_message}'"
        )

        # Estimate tokens (rough approximation)
        input_tokens = sum(len(m.content.split()) * 1.3 for m in request.messages)
        output_tokens = len(mock_content.split()) * 1.3

        return ChatResponse(
            id=f"mock-{uuid.uuid4().hex[:8]}",
            model=request.model,
            content=mock_content,
            finish_reason="stop",
            input_tokens=int(input_tokens),
            output_tokens=int(output_tokens),
        )

    async def chat_stream(
        self, request: ChatRequest, api_key: str
    ) -> AsyncIterator[str]:
        """Stream a mock response."""
        response = await self.chat(request, api_key)

        # Stream word by word
        words = response.content.split()
        for i, word in enumerate(words):
            await asyncio.sleep(0.05)  # Simulate streaming delay
            yield f'{{"choices":[{{"delta":{{"content":"{word} "}}}}]}}'

        yield '{"choices":[{"delta":{},"finish_reason":"stop"}]}'


# Singleton
mock_provider = MockProvider()
