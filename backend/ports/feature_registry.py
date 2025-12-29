"""Feature Registry Port - Interface for Feature Allowlisting.

Architecture Hexagonale: Port définissant le contrat pour la validation
des features/use-cases autorisés par application.

Le feature allowlisting permet de:
- Contrôler strictement les usages autorisés par application
- Définir des contraintes par feature (tokens, coût, modèles)
- Refuser tout usage hors scope
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class FeatureAction(str, Enum):
    """Actions possibles pour une feature."""

    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"
    SUMMARIZATION = "summarization"
    CLASSIFICATION = "classification"
    EXTRACTION = "extraction"
    TRANSLATION = "translation"
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    ANALYSIS = "analysis"
    CUSTOM = "custom"


class FeatureDecision(str, Enum):
    """Codes de décision pour la validation de feature."""

    ALLOWED = "ALLOWED"
    ALLOWED_NO_REGISTRY = "ALLOWED_NO_REGISTRY"
    ALLOWED_PERMISSIVE = "ALLOWED_PERMISSIVE"
    DENIED_UNKNOWN_FEATURE = "DENIED_UNKNOWN_FEATURE"
    DENIED_FEATURE_DISABLED = "DENIED_FEATURE_DISABLED"
    DENIED_ACTION_NOT_ALLOWED = "DENIED_ACTION_NOT_ALLOWED"
    DENIED_MODEL_NOT_ALLOWED = "DENIED_MODEL_NOT_ALLOWED"
    DENIED_ENVIRONMENT_NOT_ALLOWED = "DENIED_ENVIRONMENT_NOT_ALLOWED"
    DENIED_TOKEN_LIMIT = "DENIED_TOKEN_LIMIT"
    DENIED_COST_LIMIT = "DENIED_COST_LIMIT"
    DENIED_NO_FEATURE_SPECIFIED = "DENIED_NO_FEATURE_SPECIFIED"


@dataclass
class FeatureDefinition:
    """Définition d'une feature autorisée."""

    id: str
    name: str
    description: str = ""

    # Actions autorisées
    allowed_actions: list[FeatureAction] = field(default_factory=list)

    # Modèles autorisés (vide = tous)
    allowed_models: list[str] = field(default_factory=list)

    # Environnements autorisés
    allowed_environments: list[str] = field(
        default_factory=lambda: ["development", "staging", "production"]
    )

    # Contraintes
    max_tokens_per_request: Optional[int] = None
    max_cost_per_request_usd: Optional[float] = None
    max_requests_per_minute: Optional[int] = None

    # État
    is_active: bool = True

    # Data handling
    allow_pii: bool = False
    require_data_separation: bool = True


@dataclass
class FeatureCheckResult:
    """Résultat de la validation d'une feature."""

    allowed: bool
    decision: FeatureDecision
    reason: str

    feature_id: Optional[str] = None
    feature_name: Optional[str] = None

    # Contraintes appliquées si autorisé
    applied_constraints: dict = field(default_factory=dict)

    # Warnings (non bloquants)
    warnings: list[str] = field(default_factory=list)


class FeatureRegistryPort(ABC):
    """Port pour la gestion des features/use-cases.

    Responsabilités:
    - Valider qu'une requête est autorisée pour une feature
    - Gérer le registre des features par application
    - Appliquer les contraintes définies
    """

    @abstractmethod
    async def check_feature(
        self,
        app_id: str,
        feature_id: Optional[str],
        action: FeatureAction,
        model: str,
        environment: str,
        estimated_tokens: Optional[int] = None,
        estimated_cost_usd: Optional[float] = None,
    ) -> FeatureCheckResult:
        """Vérifie si une requête est autorisée pour une feature.

        Args:
            app_id: Identifiant de l'application
            feature_id: Identifiant de la feature (None = utilise default)
            action: Action demandée
            model: Modèle LLM demandé
            environment: Environnement (development, staging, production)
            estimated_tokens: Tokens estimés (optionnel)
            estimated_cost_usd: Coût estimé en USD (optionnel)

        Returns:
            FeatureCheckResult avec la décision et les détails
        """
        pass

    @abstractmethod
    async def register_feature(
        self,
        app_id: str,
        feature: FeatureDefinition,
    ) -> None:
        """Enregistre une feature pour une application.

        Args:
            app_id: Identifiant de l'application
            feature: Définition de la feature
        """
        pass

    @abstractmethod
    async def remove_feature(
        self,
        app_id: str,
        feature_id: str,
    ) -> bool:
        """Retire une feature du registre.

        Args:
            app_id: Identifiant de l'application
            feature_id: Identifiant de la feature

        Returns:
            True si la feature existait et a été retirée
        """
        pass

    @abstractmethod
    async def get_feature(
        self,
        app_id: str,
        feature_id: str,
    ) -> Optional[FeatureDefinition]:
        """Récupère la définition d'une feature.

        Args:
            app_id: Identifiant de l'application
            feature_id: Identifiant de la feature

        Returns:
            La définition ou None si non trouvée
        """
        pass

    @abstractmethod
    async def list_features(
        self,
        app_id: str,
    ) -> list[FeatureDefinition]:
        """Liste les features d'une application.

        Args:
            app_id: Identifiant de l'application

        Returns:
            Liste des features enregistrées
        """
        pass

    @abstractmethod
    async def set_strict_mode(
        self,
        app_id: str,
        strict: bool,
    ) -> None:
        """Configure le mode strict pour une application.

        En mode strict, les requêtes sans feature spécifiée sont refusées.
        En mode permissif, elles sont autorisées.

        Args:
            app_id: Identifiant de l'application
            strict: True pour mode strict, False pour permissif
        """
        pass

    @abstractmethod
    async def set_default_feature(
        self,
        app_id: str,
        feature_id: Optional[str],
    ) -> None:
        """Configure la feature par défaut pour une application.

        Args:
            app_id: Identifiant de l'application
            feature_id: ID de la feature par défaut (None pour aucune)
        """
        pass
