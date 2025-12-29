"""LLM Gateway SDK - Python client for LLM Gateway."""

from llm_gateway_sdk.client import LLMGateway, AsyncLLMGateway
from llm_gateway_sdk.models import (
    ChatMessage,
    ChatCompletionRequest,
    ChatCompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
)
from llm_gateway_sdk.exceptions import (
    LLMGatewayError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
    ServerError,
)

__version__ = "0.1.0"
__all__ = [
    "LLMGateway",
    "AsyncLLMGateway",
    "ChatMessage",
    "ChatCompletionRequest",
    "ChatCompletionResponse",
    "EmbeddingRequest",
    "EmbeddingResponse",
    "LLMGatewayError",
    "AuthenticationError",
    "RateLimitError",
    "ValidationError",
    "ServerError",
]
