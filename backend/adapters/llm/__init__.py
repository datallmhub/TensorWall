"""LLM Adapters - Wrappers autour des providers legacy.

Architecture Hexagonale: Ces adapters implémentent les Ports LLMProviderPort
et EmbeddingProviderPort.
"""

from backend.adapters.llm.openai_adapter import OpenAIAdapter
from backend.adapters.llm.anthropic_adapter import AnthropicAdapter
from backend.adapters.llm.ollama_adapter import OllamaAdapter
from backend.adapters.llm.mock_adapter import MockAdapter
from backend.adapters.llm.openai_embedding_adapter import OpenAIEmbeddingAdapter


__all__ = [
    # Chat adapters
    "OpenAIAdapter",
    "AnthropicAdapter",
    "OllamaAdapter",
    "MockAdapter",
    # Embedding adapters
    "OpenAIEmbeddingAdapter",
]
