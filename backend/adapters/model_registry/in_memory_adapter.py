"""In-Memory Model Registry Adapter.

Architecture Hexagonale: Implémentation native du ModelRegistryPort
avec catalogue de modèles pré-configuré.
"""

from datetime import datetime
from typing import Any

from backend.ports.model_registry import (
    ModelRegistryPort,
    ModelInfo,
    ModelPricing,
    ModelLimits,
    ModelValidation,
    ProviderType,
    ModelStatus,
    ModelCapability,
)


# Pre-configured models catalog
DEFAULT_MODELS: list[ModelInfo] = [
    # OpenAI Models
    ModelInfo(
        model_id="gpt-4o",
        name="GPT-4o",
        provider=ProviderType.OPENAI,
        provider_model_id="gpt-4o",
        description="Most advanced multimodal model",
        capabilities=[
            ModelCapability.CHAT,
            ModelCapability.VISION,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.STREAMING,
            ModelCapability.JSON_MODE,
            ModelCapability.SYSTEM_PROMPT,
        ],
        pricing=ModelPricing(input_per_million=2.50, output_per_million=10.00),
        limits=ModelLimits(
            max_context_tokens=128000, max_output_tokens=16384, max_images=10
        ),
        tags=["flagship", "multimodal"],
    ),
    ModelInfo(
        model_id="gpt-4o-mini",
        name="GPT-4o Mini",
        provider=ProviderType.OPENAI,
        provider_model_id="gpt-4o-mini",
        description="Affordable and intelligent small model",
        capabilities=[
            ModelCapability.CHAT,
            ModelCapability.VISION,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.STREAMING,
            ModelCapability.JSON_MODE,
            ModelCapability.SYSTEM_PROMPT,
        ],
        pricing=ModelPricing(input_per_million=0.15, output_per_million=0.60),
        limits=ModelLimits(max_context_tokens=128000, max_output_tokens=16384),
        tags=["affordable", "fast"],
    ),
    ModelInfo(
        model_id="gpt-4-turbo",
        name="GPT-4 Turbo",
        provider=ProviderType.OPENAI,
        provider_model_id="gpt-4-turbo",
        description="GPT-4 Turbo with vision",
        capabilities=[
            ModelCapability.CHAT,
            ModelCapability.VISION,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.STREAMING,
            ModelCapability.JSON_MODE,
            ModelCapability.SYSTEM_PROMPT,
        ],
        pricing=ModelPricing(input_per_million=10.00, output_per_million=30.00),
        limits=ModelLimits(max_context_tokens=128000, max_output_tokens=4096),
        tags=["vision", "turbo"],
    ),
    ModelInfo(
        model_id="gpt-3.5-turbo",
        name="GPT-3.5 Turbo",
        provider=ProviderType.OPENAI,
        provider_model_id="gpt-3.5-turbo",
        description="Fast and cost-effective model",
        capabilities=[
            ModelCapability.CHAT,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.STREAMING,
            ModelCapability.JSON_MODE,
            ModelCapability.SYSTEM_PROMPT,
        ],
        pricing=ModelPricing(input_per_million=0.50, output_per_million=1.50),
        limits=ModelLimits(max_context_tokens=16385, max_output_tokens=4096),
        tags=["affordable", "fast", "legacy"],
    ),
    ModelInfo(
        model_id="text-embedding-3-large",
        name="Text Embedding 3 Large",
        provider=ProviderType.OPENAI,
        provider_model_id="text-embedding-3-large",
        description="Most capable embedding model",
        capabilities=[ModelCapability.EMBEDDING],
        pricing=ModelPricing(input_per_million=0.13, output_per_million=0.0),
        limits=ModelLimits(max_context_tokens=8191, max_output_tokens=0),
        tags=["embedding", "large"],
    ),
    ModelInfo(
        model_id="text-embedding-3-small",
        name="Text Embedding 3 Small",
        provider=ProviderType.OPENAI,
        provider_model_id="text-embedding-3-small",
        description="Efficient embedding model",
        capabilities=[ModelCapability.EMBEDDING],
        pricing=ModelPricing(input_per_million=0.02, output_per_million=0.0),
        limits=ModelLimits(max_context_tokens=8191, max_output_tokens=0),
        tags=["embedding", "affordable"],
    ),
    # Anthropic Models
    ModelInfo(
        model_id="claude-3-5-sonnet",
        name="Claude 3.5 Sonnet",
        provider=ProviderType.ANTHROPIC,
        provider_model_id="claude-3-5-sonnet-20241022",
        description="Most intelligent Claude model",
        capabilities=[
            ModelCapability.CHAT,
            ModelCapability.VISION,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.STREAMING,
            ModelCapability.SYSTEM_PROMPT,
        ],
        pricing=ModelPricing(input_per_million=3.00, output_per_million=15.00),
        limits=ModelLimits(
            max_context_tokens=200000, max_output_tokens=8192, max_images=20
        ),
        tags=["flagship", "multimodal"],
    ),
    ModelInfo(
        model_id="claude-3-5-haiku",
        name="Claude 3.5 Haiku",
        provider=ProviderType.ANTHROPIC,
        provider_model_id="claude-3-5-haiku-20241022",
        description="Fast and affordable Claude model",
        capabilities=[
            ModelCapability.CHAT,
            ModelCapability.VISION,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.STREAMING,
            ModelCapability.SYSTEM_PROMPT,
        ],
        pricing=ModelPricing(input_per_million=0.80, output_per_million=4.00),
        limits=ModelLimits(max_context_tokens=200000, max_output_tokens=8192),
        tags=["affordable", "fast"],
    ),
    ModelInfo(
        model_id="claude-3-opus",
        name="Claude 3 Opus",
        provider=ProviderType.ANTHROPIC,
        provider_model_id="claude-3-opus-20240229",
        description="Most powerful Claude for complex tasks",
        capabilities=[
            ModelCapability.CHAT,
            ModelCapability.VISION,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.STREAMING,
            ModelCapability.SYSTEM_PROMPT,
        ],
        pricing=ModelPricing(input_per_million=15.00, output_per_million=75.00),
        limits=ModelLimits(max_context_tokens=200000, max_output_tokens=4096),
        tags=["powerful", "complex-tasks"],
    ),
    # Mistral Models
    ModelInfo(
        model_id="mistral-large",
        name="Mistral Large",
        provider=ProviderType.MISTRAL,
        provider_model_id="mistral-large-latest",
        description="Mistral flagship model",
        capabilities=[
            ModelCapability.CHAT,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.STREAMING,
            ModelCapability.JSON_MODE,
            ModelCapability.SYSTEM_PROMPT,
        ],
        pricing=ModelPricing(input_per_million=2.00, output_per_million=6.00),
        limits=ModelLimits(max_context_tokens=128000, max_output_tokens=4096),
        tags=["flagship"],
    ),
    ModelInfo(
        model_id="mistral-small",
        name="Mistral Small",
        provider=ProviderType.MISTRAL,
        provider_model_id="mistral-small-latest",
        description="Fast and efficient Mistral model",
        capabilities=[
            ModelCapability.CHAT,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.STREAMING,
            ModelCapability.SYSTEM_PROMPT,
        ],
        pricing=ModelPricing(input_per_million=0.20, output_per_million=0.60),
        limits=ModelLimits(max_context_tokens=32000, max_output_tokens=4096),
        tags=["affordable", "fast"],
    ),
]

# Model aliases
DEFAULT_ALIASES: dict[str, str] = {
    "gpt-4": "gpt-4-turbo",
    "gpt-4o-latest": "gpt-4o",
    "claude-3-sonnet": "claude-3-5-sonnet",
    "claude-sonnet": "claude-3-5-sonnet",
    "claude-haiku": "claude-3-5-haiku",
    "claude-opus": "claude-3-opus",
    "mistral": "mistral-large",
}


class InMemoryModelRegistryAdapter(ModelRegistryPort):
    """
    In-memory model registry with pre-configured catalog.

    Provides default models for OpenAI, Anthropic, and Mistral.
    Supports dynamic discovery for local providers.
    """

    def __init__(
        self,
        load_defaults: bool = True,
        http_client: Any = None,
    ):
        """
        Initialize the adapter.

        Args:
            load_defaults: Whether to load default model catalog
            http_client: Optional HTTP client for local discovery
        """
        self._models: dict[str, ModelInfo] = {}
        self._aliases: dict[str, str] = dict(DEFAULT_ALIASES)
        self._http_client = http_client

        if load_defaults:
            for model in DEFAULT_MODELS:
                model.added_at = datetime.now()
                self._models[model.model_id] = model

    async def list_models(
        self,
        provider: ProviderType | None = None,
        capability: ModelCapability | None = None,
        status: ModelStatus | None = None,
        tags: list[str] | None = None,
    ) -> list[ModelInfo]:
        """List models with optional filters."""
        results = list(self._models.values())

        if provider:
            results = [m for m in results if m.provider == provider]
        if capability:
            results = [m for m in results if capability in m.capabilities]
        if status:
            results = [m for m in results if m.status == status]
        if tags:
            results = [m for m in results if any(t in m.tags for t in tags)]

        return sorted(results, key=lambda m: m.name)

    async def get_model(
        self,
        model_id: str,
    ) -> ModelInfo | None:
        """Get a model by ID."""
        # Check direct ID first
        if model_id in self._models:
            return self._models[model_id]

        # Try alias
        resolved = await self.resolve_model_alias(model_id)
        if resolved and resolved in self._models:
            return self._models[resolved]

        return None

    async def get_model_by_provider_id(
        self,
        provider: ProviderType,
        provider_model_id: str,
    ) -> ModelInfo | None:
        """Get a model by provider ID."""
        for model in self._models.values():
            if (
                model.provider == provider
                and model.provider_model_id == provider_model_id
            ):
                return model
        return None

    async def validate_model(
        self,
        model_id: str,
        capability: ModelCapability | None = None,
    ) -> ModelValidation:
        """Validate a model."""
        model = await self.get_model(model_id)

        if not model:
            # Try to find similar models
            suggested = None
            for m in self._models.values():
                if model_id.lower() in m.model_id.lower():
                    suggested = m.model_id
                    break

            return ModelValidation(
                valid=False,
                model_id=model_id,
                reason=f"Model '{model_id}' not found",
                suggested_model=suggested,
            )

        if model.status == ModelStatus.UNAVAILABLE:
            return ModelValidation(
                valid=False,
                model_id=model_id,
                provider=model.provider,
                reason="Model is currently unavailable",
            )

        if model.status == ModelStatus.DEPRECATED:
            suggested = model.metadata.get("replacement")
            return ModelValidation(
                valid=True,  # Still usable but deprecated
                model_id=model_id,
                provider=model.provider,
                reason="Model is deprecated",
                suggested_model=suggested,
            )

        if capability and capability not in model.capabilities:
            return ModelValidation(
                valid=False,
                model_id=model_id,
                provider=model.provider,
                reason=f"Model does not support capability: {capability.value}",
            )

        return ModelValidation(
            valid=True,
            model_id=model_id,
            provider=model.provider,
        )

    async def resolve_model_alias(
        self,
        alias: str,
    ) -> str | None:
        """Resolve a model alias."""
        if alias in self._models:
            return alias
        return self._aliases.get(alias)

    async def register_model(
        self,
        model: ModelInfo,
    ) -> ModelInfo:
        """Register a new model."""
        model.added_at = datetime.now()
        model.updated_at = datetime.now()
        self._models[model.model_id] = model
        return model

    async def update_model(
        self,
        model_id: str,
        status: ModelStatus | None = None,
        pricing: ModelPricing | None = None,
        limits: ModelLimits | None = None,
        tags: list[str] | None = None,
    ) -> ModelInfo:
        """Update a model."""
        if model_id not in self._models:
            raise ValueError(f"Model {model_id} not found")

        model = self._models[model_id]

        if status:
            model.status = status
        if pricing:
            model.pricing = pricing
        if limits:
            model.limits = limits
        if tags:
            model.tags = tags

        model.updated_at = datetime.now()
        return model

    async def deprecate_model(
        self,
        model_id: str,
        suggested_replacement: str | None = None,
    ) -> ModelInfo:
        """Deprecate a model."""
        if model_id not in self._models:
            raise ValueError(f"Model {model_id} not found")

        model = self._models[model_id]
        model.status = ModelStatus.DEPRECATED
        model.deprecated_at = datetime.now()
        model.updated_at = datetime.now()

        if suggested_replacement:
            model.metadata["replacement"] = suggested_replacement

        return model

    async def remove_model(
        self,
        model_id: str,
    ) -> bool:
        """Remove a model."""
        if model_id not in self._models:
            return False
        del self._models[model_id]
        return True

    async def discover_local_models(
        self,
        provider: ProviderType,
        base_url: str | None = None,
    ) -> list[ModelInfo]:
        """Discover local models."""
        if not self._http_client:
            return []

        discovered = []

        try:
            if provider == ProviderType.OLLAMA:
                url = base_url or "http://localhost:11434"
                response = await self._http_client.get(f"{url}/api/tags")
                data = response.json()

                for model in data.get("models", []):
                    model_info = ModelInfo(
                        model_id=f"ollama:{model['name']}",
                        name=model["name"],
                        provider=ProviderType.OLLAMA,
                        provider_model_id=model["name"],
                        description=f"Ollama local model: {model['name']}",
                        capabilities=[
                            ModelCapability.CHAT,
                            ModelCapability.STREAMING,
                        ],
                        base_url=url,
                        tags=["local", "ollama"],
                    )
                    discovered.append(model_info)

            elif provider == ProviderType.LMSTUDIO:
                url = base_url or "http://localhost:1234"
                response = await self._http_client.get(f"{url}/v1/models")
                data = response.json()

                for model in data.get("data", []):
                    model_info = ModelInfo(
                        model_id=f"lmstudio:{model['id']}",
                        name=model.get("id", "Unknown"),
                        provider=ProviderType.LMSTUDIO,
                        provider_model_id=model["id"],
                        description=f"LM Studio local model: {model['id']}",
                        capabilities=[
                            ModelCapability.CHAT,
                            ModelCapability.STREAMING,
                        ],
                        base_url=url,
                        tags=["local", "lmstudio"],
                    )
                    discovered.append(model_info)

        except Exception:
            pass

        return discovered

    async def sync_provider_models(
        self,
        provider: ProviderType,
    ) -> int:
        """Sync models from a provider."""
        discovered = await self.discover_local_models(provider)

        for model in discovered:
            if model.model_id not in self._models:
                await self.register_model(model)

        return len(discovered)

    async def estimate_cost(
        self,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Estimate cost for a request."""
        model = await self.get_model(model_id)
        if not model:
            return 0.0

        input_cost = (input_tokens / 1_000_000) * model.pricing.input_per_million
        output_cost = (output_tokens / 1_000_000) * model.pricing.output_per_million

        return input_cost + output_cost

    async def get_pricing(
        self,
        model_id: str,
    ) -> ModelPricing | None:
        """Get pricing for a model."""
        model = await self.get_model(model_id)
        return model.pricing if model else None

    def add_alias(self, alias: str, model_id: str) -> None:
        """Add a model alias."""
        self._aliases[alias] = model_id

    def clear(self) -> None:
        """Clear all models."""
        self._models.clear()
        self._aliases.clear()
