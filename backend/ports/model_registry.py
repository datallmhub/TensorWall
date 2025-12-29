"""Model Registry Port - Interface Abstraite.

Architecture Hexagonale: Port pour le catalogue des modèles LLM.

Fonctionnalités:
- Catalogue des modèles disponibles
- Métadonnées des modèles (capabilities, pricing)
- Validation des modèles
- Discovery dynamique (Ollama, LM Studio)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ProviderType(str, Enum):
    """Types de fournisseurs LLM."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MISTRAL = "mistral"
    OLLAMA = "ollama"
    LMSTUDIO = "lmstudio"
    AZURE_OPENAI = "azure_openai"
    AWS_BEDROCK = "aws_bedrock"
    GROQ = "groq"
    TOGETHER = "together"
    GOOGLE = "google"
    COHERE = "cohere"
    DEEPSEEK = "deepseek"
    XAI = "xai"
    CUSTOM = "custom"


class ModelStatus(str, Enum):
    """Statut d'un modèle."""

    AVAILABLE = "available"
    DEPRECATED = "deprecated"
    PREVIEW = "preview"
    UNAVAILABLE = "unavailable"


class ModelCapability(str, Enum):
    """Capacités des modèles."""

    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"
    VISION = "vision"
    FUNCTION_CALLING = "function_calling"
    STREAMING = "streaming"
    JSON_MODE = "json_mode"
    SYSTEM_PROMPT = "system_prompt"


@dataclass
class ModelPricing:
    """Tarification d'un modèle (par million de tokens)."""

    input_per_million: float = 0.0
    output_per_million: float = 0.0
    currency: str = "USD"
    cached_input_per_million: float | None = None
    batch_input_per_million: float | None = None
    batch_output_per_million: float | None = None


@dataclass
class ModelLimits:
    """Limites d'un modèle."""

    max_context_tokens: int = 4096
    max_output_tokens: int = 4096
    max_images: int = 0
    requests_per_minute: int | None = None
    tokens_per_minute: int | None = None


@dataclass
class ModelInfo:
    """Informations complètes d'un modèle."""

    model_id: str
    name: str
    provider: ProviderType
    provider_model_id: str  # ID utilisé par l'API du provider
    description: str = ""
    status: ModelStatus = ModelStatus.AVAILABLE
    capabilities: list[ModelCapability] = field(default_factory=list)
    pricing: ModelPricing = field(default_factory=ModelPricing)
    limits: ModelLimits = field(default_factory=ModelLimits)

    # Optionnel
    base_url: str | None = None  # Pour endpoints custom
    api_key_env_var: str | None = None  # Variable d'env pour la clé
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    # Dates
    added_at: datetime | None = None
    updated_at: datetime | None = None
    deprecated_at: datetime | None = None


@dataclass
class ModelValidation:
    """Résultat de validation d'un modèle."""

    valid: bool
    model_id: str
    provider: ProviderType | None = None
    reason: str | None = None
    suggested_model: str | None = None


class ModelRegistryPort(ABC):
    """
    Port abstrait pour le registre des modèles.

    Gère le catalogue des modèles LLM disponibles,
    leurs métadonnées et leur validation.
    """

    # -------------------------------------------------------------------------
    # Model Discovery
    # -------------------------------------------------------------------------

    @abstractmethod
    async def list_models(
        self,
        provider: ProviderType | None = None,
        capability: ModelCapability | None = None,
        status: ModelStatus | None = None,
        tags: list[str] | None = None,
    ) -> list[ModelInfo]:
        """
        Liste les modèles disponibles.

        Args:
            provider: Filtrer par fournisseur
            capability: Filtrer par capacité
            status: Filtrer par statut
            tags: Filtrer par tags

        Returns:
            Liste des modèles correspondants
        """
        ...

    @abstractmethod
    async def get_model(
        self,
        model_id: str,
    ) -> ModelInfo | None:
        """
        Récupère un modèle par ID.

        Args:
            model_id: Identifiant du modèle

        Returns:
            Informations du modèle ou None
        """
        ...

    @abstractmethod
    async def get_model_by_provider_id(
        self,
        provider: ProviderType,
        provider_model_id: str,
    ) -> ModelInfo | None:
        """
        Récupère un modèle par son ID provider.

        Args:
            provider: Fournisseur
            provider_model_id: ID du modèle chez le fournisseur

        Returns:
            Informations du modèle ou None
        """
        ...

    # -------------------------------------------------------------------------
    # Model Validation
    # -------------------------------------------------------------------------

    @abstractmethod
    async def validate_model(
        self,
        model_id: str,
        capability: ModelCapability | None = None,
    ) -> ModelValidation:
        """
        Valide qu'un modèle existe et est utilisable.

        Args:
            model_id: Identifiant du modèle
            capability: Capacité requise

        Returns:
            Résultat de validation
        """
        ...

    @abstractmethod
    async def resolve_model_alias(
        self,
        alias: str,
    ) -> str | None:
        """
        Résout un alias de modèle vers l'ID réel.

        Ex: "gpt-4" -> "gpt-4-turbo-2024-04-09"

        Args:
            alias: Alias ou ID du modèle

        Returns:
            ID réel ou None si non trouvé
        """
        ...

    # -------------------------------------------------------------------------
    # Model Management
    # -------------------------------------------------------------------------

    @abstractmethod
    async def register_model(
        self,
        model: ModelInfo,
    ) -> ModelInfo:
        """
        Enregistre un nouveau modèle.

        Args:
            model: Informations du modèle

        Returns:
            Modèle enregistré
        """
        ...

    @abstractmethod
    async def update_model(
        self,
        model_id: str,
        status: ModelStatus | None = None,
        pricing: ModelPricing | None = None,
        limits: ModelLimits | None = None,
        tags: list[str] | None = None,
    ) -> ModelInfo:
        """
        Met à jour un modèle.

        Args:
            model_id: ID du modèle
            status: Nouveau statut
            pricing: Nouvelle tarification
            limits: Nouvelles limites
            tags: Nouveaux tags

        Returns:
            Modèle mis à jour
        """
        ...

    @abstractmethod
    async def deprecate_model(
        self,
        model_id: str,
        suggested_replacement: str | None = None,
    ) -> ModelInfo:
        """
        Marque un modèle comme déprécié.

        Args:
            model_id: ID du modèle
            suggested_replacement: Modèle de remplacement suggéré

        Returns:
            Modèle mis à jour
        """
        ...

    @abstractmethod
    async def remove_model(
        self,
        model_id: str,
    ) -> bool:
        """
        Supprime un modèle du registre.

        Args:
            model_id: ID du modèle

        Returns:
            True si supprimé
        """
        ...

    # -------------------------------------------------------------------------
    # Dynamic Discovery
    # -------------------------------------------------------------------------

    @abstractmethod
    async def discover_local_models(
        self,
        provider: ProviderType,
        base_url: str | None = None,
    ) -> list[ModelInfo]:
        """
        Découvre les modèles disponibles localement.

        Pour Ollama, LM Studio, etc.

        Args:
            provider: Type de fournisseur local
            base_url: URL de base du serveur

        Returns:
            Liste des modèles découverts
        """
        ...

    @abstractmethod
    async def sync_provider_models(
        self,
        provider: ProviderType,
    ) -> int:
        """
        Synchronise les modèles depuis un fournisseur.

        Args:
            provider: Fournisseur à synchroniser

        Returns:
            Nombre de modèles synchronisés
        """
        ...

    # -------------------------------------------------------------------------
    # Pricing Utilities
    # -------------------------------------------------------------------------

    @abstractmethod
    async def estimate_cost(
        self,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """
        Estime le coût d'une requête.

        Args:
            model_id: ID du modèle
            input_tokens: Tokens d'entrée
            output_tokens: Tokens de sortie

        Returns:
            Coût estimé en USD
        """
        ...

    @abstractmethod
    async def get_pricing(
        self,
        model_id: str,
    ) -> ModelPricing | None:
        """
        Récupère la tarification d'un modèle.

        Args:
            model_id: ID du modèle

        Returns:
            Tarification ou None
        """
        ...
