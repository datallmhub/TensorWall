from backend.application.providers.base import LLMProvider, ChatRequest, ChatResponse, ChatMessage
from backend.application.providers.openai import openai_provider, OpenAIProvider
from backend.application.providers.anthropic import anthropic_provider, AnthropicProvider
from backend.application.providers.ollama import ollama_provider, OllamaProvider
from backend.application.providers.lmstudio import lmstudio_provider, LMStudioProvider
from backend.application.providers.bedrock import bedrock_provider, BedrockProvider
from backend.core.config import settings


def get_provider(model: str) -> LLMProvider:
    """Get the appropriate provider for a model."""
    # Mock provider only available in test environment
    if settings.environment == "test":
        from backend.application.providers.mock import mock_provider

        if mock_provider.supports_model(model):
            return mock_provider

    # Check explicit provider prefixes first (lmstudio/, ollama/, bedrock/)
    # This ensures models with explicit prefixes are routed correctly
    if model.startswith("lmstudio/"):
        return lmstudio_provider
    elif model.startswith("ollama/"):
        return ollama_provider
    elif model.startswith("bedrock/"):
        return bedrock_provider
    # Then check by model name patterns
    elif lmstudio_provider.supports_model(model):
        return lmstudio_provider
    elif ollama_provider.supports_model(model):
        return ollama_provider
    elif bedrock_provider.supports_model(model):
        return bedrock_provider
    elif openai_provider.supports_model(model):
        return openai_provider
    elif anthropic_provider.supports_model(model):
        return anthropic_provider
    else:
        raise ValueError(f"No provider found for model: {model}")


__all__ = [
    "LLMProvider",
    "ChatRequest",
    "ChatResponse",
    "ChatMessage",
    "OpenAIProvider",
    "openai_provider",
    "AnthropicProvider",
    "anthropic_provider",
    "OllamaProvider",
    "ollama_provider",
    "LMStudioProvider",
    "lmstudio_provider",
    "BedrockProvider",
    "bedrock_provider",
    "get_provider",
]
