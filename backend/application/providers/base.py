from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional
from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    stream: bool = False


class ChatResponse(BaseModel):
    id: str
    model: str
    content: str
    input_tokens: int
    output_tokens: int
    finish_reason: str


class LLMProvider(ABC):
    """Base class for LLM providers."""

    @abstractmethod
    async def chat(self, request: ChatRequest, api_key: str) -> ChatResponse:
        """Send a chat completion request."""
        pass

    @abstractmethod
    async def chat_stream(
        self, request: ChatRequest, api_key: str
    ) -> AsyncIterator[str]:
        """Send a streaming chat completion request."""
        pass

    @abstractmethod
    def supports_model(self, model: str) -> bool:
        """Check if provider supports the given model."""
        pass
