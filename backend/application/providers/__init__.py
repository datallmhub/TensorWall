from backend.application.providers.base import LLMProvider, ChatRequest, ChatResponse, ChatMessage
from backend.application.providers.openai import openai_provider, OpenAIProvider
from backend.application.providers.anthropic import anthropic_provider, AnthropicProvider
from backend.application.providers.ollama import ollama_provider, OllamaProvider
from backend.application.providers.lmstudio import lmstudio_provider, LMStudioProvider
from backend.application.providers.bedrock import bedrock_provider, BedrockProvider
from backend.application.providers.azure_openai import azure_openai_provider, AzureOpenAIProvider
from backend.application.providers.vertex import vertex_ai_provider, VertexAIProvider
from backend.application.providers.groq import groq_provider, GroqProvider
from backend.application.providers.mistral import mistral_provider, MistralProvider
from backend.core.config import settings


def get_provider(model: str) -> LLMProvider:
    """Get the appropriate provider for a model."""
    # Mock provider only available in test environment
    if settings.environment == "test":
        from backend.application.providers.mock import mock_provider

        if mock_provider.supports_model(model):
            return mock_provider

    # Check explicit provider prefixes first
    if model.startswith("lmstudio/"):
        return lmstudio_provider
    elif model.startswith("ollama/"):
        return ollama_provider
    elif model.startswith("bedrock/"):
        return bedrock_provider
    elif model.startswith("azure/") or model.startswith("azure-"):
        return azure_openai_provider
    elif model.startswith("vertex/"):
        return vertex_ai_provider
    elif model.startswith("groq/"):
        return groq_provider
    elif model.startswith("mistral/"):
        return mistral_provider

    # Then check by model name patterns
    elif lmstudio_provider.supports_model(model):
        return lmstudio_provider
    elif ollama_provider.supports_model(model):
        return ollama_provider
    elif bedrock_provider.supports_model(model):
        return bedrock_provider
    elif groq_provider.supports_model(model):
        return groq_provider
    elif mistral_provider.supports_model(model):
        return mistral_provider
    elif vertex_ai_provider.supports_model(model):
        return vertex_ai_provider
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
    "AzureOpenAIProvider",
    "azure_openai_provider",
    "VertexAIProvider",
    "vertex_ai_provider",
    "GroqProvider",
    "groq_provider",
    "MistralProvider",
    "mistral_provider",
    "get_provider",
]
