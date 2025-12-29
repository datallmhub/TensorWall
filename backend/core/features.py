"""
Use-case / Feature Allowlisting - Feature control for TensorWall.

Ce module implémente le contrôle STRICT des usages autorisés:
- Chaque application doit déclarer ses features/use-cases
- Chaque feature définit les actions et modèles autorisés
- Tout usage hors scope est refusé par défaut

Uses ConditionMatcher for unified validation logic.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from backend.core.base import ConditionMatcher

logger = logging.getLogger(__name__)


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


class FeatureDefinition(BaseModel):
    """Définition d'une feature/use-case autorisée."""

    id: str
    name: str
    description: str

    # Actions autorisées pour cette feature
    allowed_actions: list[FeatureAction]

    # Modèles autorisés (vide = tous ceux de l'app)
    allowed_models: list[str] = []

    # Contraintes spécifiques
    max_tokens_per_request: Optional[int] = None
    max_requests_per_minute: Optional[int] = None
    max_cost_per_request_usd: Optional[float] = None

    # Environnements où cette feature est active
    allowed_environments: list[str] = ["development", "staging", "production"]

    # Metadata
    owner: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True

    # Data handling
    allow_pii: bool = False
    require_data_separation: bool = True  # Enforce instruction/data separation


class ApplicationFeatureRegistry(BaseModel):
    """Registre des features autorisées pour une application."""

    app_id: str
    organization_id: Optional[str] = None

    # Features déclarées
    features: dict[str, FeatureDefinition] = {}

    # Default feature si non spécifiée (None = refus)
    default_feature_id: Optional[str] = None

    # Mode strict: refuse si feature non déclarée
    strict_mode: bool = True

    # Audit
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class FeatureValidationResult(BaseModel):
    """Résultat de validation d'une feature."""

    allowed: bool
    feature_id: Optional[str] = None
    feature_name: Optional[str] = None

    # Decision explainability
    decision_code: str  # ALLOWED, DENIED_UNKNOWN_FEATURE, DENIED_ACTION_NOT_ALLOWED, etc.
    reason: str

    # Contraintes appliquées
    applied_constraints: dict = {}

    # Pour debug
    checked_at: datetime = Field(default_factory=datetime.utcnow)


class FeatureEnforcementError(Exception):
    """Erreur de validation de feature."""

    def __init__(self, result: FeatureValidationResult):
        self.result = result
        super().__init__(result.reason)


class FeatureRegistry:
    """
    Gestionnaire central des features/use-cases.

    Responsabilités:
    - Charger les features depuis la base de données
    - Valider chaque requête contre le registre
    - Appliquer les contraintes spécifiques
    """

    def __init__(self):
        self._registries: dict[str, ApplicationFeatureRegistry] = {}
        self._loaded_from_db: bool = False

    async def load_from_db(self, app_id: str) -> Optional[ApplicationFeatureRegistry]:
        """Charge les features d'une application depuis la DB."""
        try:
            from backend.db.session import get_db_context
            from backend.db.models import Feature
            from sqlalchemy import select

            async with get_db_context() as db:
                stmt = select(Feature).where(Feature.app_id == app_id)
                result = await db.execute(stmt)
                db_features = result.scalars().all()

                if not db_features:
                    # Pas de features = mode permissif (tout autorisé)
                    registry = ApplicationFeatureRegistry(
                        app_id=app_id,
                        strict_mode=False,  # Permissive when no features defined
                        features={},
                        default_feature_id=None,
                    )
                else:
                    features = {}
                    default_feature_id = None

                    for f in db_features:
                        # Convert allowed_actions strings to FeatureAction enums
                        allowed_actions = []
                        for action_str in f.allowed_actions or []:
                            try:
                                allowed_actions.append(FeatureAction(action_str))
                            except ValueError:
                                pass  # Skip invalid actions

                        feature_def = FeatureDefinition(
                            id=f.feature_id,
                            name=f.name,
                            description=f.description or "",
                            allowed_actions=allowed_actions,
                            allowed_models=f.allowed_models or [],
                            max_tokens_per_request=f.max_tokens_per_request,
                            max_cost_per_request_usd=f.max_cost_per_request,
                            allowed_environments=f.allowed_environments
                            or ["development", "staging", "production"],
                            is_active=f.is_enabled,
                            require_data_separation=f.require_contract,
                        )
                        features[f.feature_id] = feature_def

                        # First feature with chat action becomes default
                        if not default_feature_id and FeatureAction.CHAT in allowed_actions:
                            default_feature_id = f.feature_id

                    registry = ApplicationFeatureRegistry(
                        app_id=app_id,
                        strict_mode=True,
                        features=features,
                        default_feature_id=default_feature_id,
                    )

                self._registries[app_id] = registry
                return registry

        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(
                f"Failed to load features from DB for {app_id}: {e}"
            )
            # Return permissive registry on DB error
            registry = ApplicationFeatureRegistry(
                app_id=app_id,
                strict_mode=False,
                features={},
            )
            self._registries[app_id] = registry
            return registry

    async def get_registry_async(self, app_id: str) -> Optional[ApplicationFeatureRegistry]:
        """Get registry, loading from DB if needed."""
        if app_id not in self._registries:
            await self.load_from_db(app_id)
        return self._registries.get(app_id)

    def register_app(self, registry: ApplicationFeatureRegistry) -> None:
        """Enregistre un registre de features pour une application."""
        registry.updated_at = datetime.utcnow()
        self._registries[registry.app_id] = registry

    def add_feature(self, app_id: str, feature: FeatureDefinition) -> bool:
        """Ajoute une feature à une application."""
        if app_id not in self._registries:
            return False
        self._registries[app_id].features[feature.id] = feature
        self._registries[app_id].updated_at = datetime.utcnow()
        return True

    def remove_feature(self, app_id: str, feature_id: str) -> bool:
        """Retire une feature d'une application."""
        if app_id not in self._registries:
            return False
        if feature_id in self._registries[app_id].features:
            del self._registries[app_id].features[feature_id]
            self._registries[app_id].updated_at = datetime.utcnow()
            return True
        return False

    def get_registry(self, app_id: str) -> Optional[ApplicationFeatureRegistry]:
        """Récupère le registre d'une application."""
        return self._registries.get(app_id)

    async def validate_request_async(
        self,
        app_id: str,
        feature_id: Optional[str],
        action: FeatureAction,
        model: str,
        environment: str,
        estimated_tokens: Optional[int] = None,
        estimated_cost_usd: Optional[float] = None,
    ) -> FeatureValidationResult:
        """
        Valide une requête contre le registre de features (version async).

        Returns:
            FeatureValidationResult avec décision et explication
        """
        # 1. Charger le registre depuis la DB si pas en cache
        registry = await self.get_registry_async(app_id)
        return self._do_validate(
            registry,
            app_id,
            feature_id,
            action,
            model,
            environment,
            estimated_tokens,
            estimated_cost_usd,
        )

    def validate_request(
        self,
        app_id: str,
        feature_id: Optional[str],
        action: FeatureAction,
        model: str,
        environment: str,
        estimated_tokens: Optional[int] = None,
        estimated_cost_usd: Optional[float] = None,
    ) -> FeatureValidationResult:
        """
        Valide une requête contre le registre de features (version sync - utilise le cache).

        Returns:
            FeatureValidationResult avec décision et explication
        """
        # Utilise le cache uniquement (pour backward compat)
        registry = self._registries.get(app_id)
        return self._do_validate(
            registry,
            app_id,
            feature_id,
            action,
            model,
            environment,
            estimated_tokens,
            estimated_cost_usd,
        )

    def _do_validate(
        self,
        registry: Optional[ApplicationFeatureRegistry],
        app_id: str,
        feature_id: Optional[str],
        action: FeatureAction,
        model: str,
        environment: str,
        estimated_tokens: Optional[int] = None,
        estimated_cost_usd: Optional[float] = None,
    ) -> FeatureValidationResult:
        """Logic de validation commune."""

        if not registry:
            # App sans registre = mode permissif (backward compat)
            return FeatureValidationResult(
                allowed=True,
                decision_code="ALLOWED_NO_REGISTRY",
                reason=f"Application {app_id} has no feature registry (permissive mode)",
            )

        # 2. Résoudre la feature ("unknown" = no feature specified)
        effective_feature_id = None if feature_id in (None, "", "unknown") else feature_id
        resolved_feature_id = effective_feature_id or registry.default_feature_id

        if not resolved_feature_id:
            if registry.strict_mode:
                return FeatureValidationResult(
                    allowed=False,
                    decision_code="DENIED_NO_FEATURE_SPECIFIED",
                    reason="No feature specified and no default feature configured (strict mode)",
                )
            else:
                return FeatureValidationResult(
                    allowed=True,
                    decision_code="ALLOWED_PERMISSIVE_MODE",
                    reason="No feature specified but strict mode is disabled",
                )

        # 3. Vérifier si la feature existe
        feature = registry.features.get(resolved_feature_id)

        if not feature:
            if registry.strict_mode:
                return FeatureValidationResult(
                    allowed=False,
                    feature_id=resolved_feature_id,
                    decision_code="DENIED_UNKNOWN_FEATURE",
                    reason=f"Feature '{resolved_feature_id}' is not registered for application {app_id}",
                )
            else:
                return FeatureValidationResult(
                    allowed=True,
                    feature_id=resolved_feature_id,
                    decision_code="ALLOWED_UNKNOWN_FEATURE_PERMISSIVE",
                    reason=f"Feature '{resolved_feature_id}' unknown but strict mode disabled",
                )

        # 4. Vérifier si la feature est active
        if not feature.is_active:
            return FeatureValidationResult(
                allowed=False,
                feature_id=feature.id,
                feature_name=feature.name,
                decision_code="DENIED_FEATURE_DISABLED",
                reason=f"Feature '{feature.name}' is currently disabled",
            )

        # 5. Vérifier l'action
        if action not in feature.allowed_actions:
            return FeatureValidationResult(
                allowed=False,
                feature_id=feature.id,
                feature_name=feature.name,
                decision_code="DENIED_ACTION_NOT_ALLOWED",
                reason=f"Action '{action.value}' is not allowed for feature '{feature.name}'. Allowed: {[a.value for a in feature.allowed_actions]}",
            )

        # 6. Vérifier le modèle using ConditionMatcher
        if feature.allowed_models:
            ok, reason = ConditionMatcher.matches_model(model, allowed=feature.allowed_models)
            if not ok:
                return FeatureValidationResult(
                    allowed=False,
                    feature_id=feature.id,
                    feature_name=feature.name,
                    decision_code="DENIED_MODEL_NOT_ALLOWED",
                    reason=f"Model '{model}' is not allowed for feature '{feature.name}'. Allowed: {feature.allowed_models}",
                )

        # 7. Vérifier l'environnement using ConditionMatcher
        ok, reason = ConditionMatcher.matches_environment(
            environment, allowed=feature.allowed_environments
        )
        if not ok:
            return FeatureValidationResult(
                allowed=False,
                feature_id=feature.id,
                feature_name=feature.name,
                decision_code="DENIED_ENVIRONMENT_NOT_ALLOWED",
                reason=f"Feature '{feature.name}' is not available in '{environment}' environment. Allowed: {feature.allowed_environments}",
            )

        # 8. Vérifier les contraintes de tokens
        if feature.max_tokens_per_request and estimated_tokens:
            if estimated_tokens > feature.max_tokens_per_request:
                return FeatureValidationResult(
                    allowed=False,
                    feature_id=feature.id,
                    feature_name=feature.name,
                    decision_code="DENIED_TOKEN_LIMIT_EXCEEDED",
                    reason=f"Estimated tokens ({estimated_tokens}) exceeds feature limit ({feature.max_tokens_per_request})",
                    applied_constraints={"max_tokens": feature.max_tokens_per_request},
                )

        # 9. Vérifier les contraintes de coût
        if feature.max_cost_per_request_usd and estimated_cost_usd:
            if estimated_cost_usd > feature.max_cost_per_request_usd:
                return FeatureValidationResult(
                    allowed=False,
                    feature_id=feature.id,
                    feature_name=feature.name,
                    decision_code="DENIED_COST_LIMIT_EXCEEDED",
                    reason=f"Estimated cost (${estimated_cost_usd:.4f}) exceeds feature limit (${feature.max_cost_per_request_usd:.4f})",
                    applied_constraints={"max_cost_usd": feature.max_cost_per_request_usd},
                )

        # 10. Tout est OK
        applied_constraints = {}
        if feature.max_tokens_per_request:
            applied_constraints["max_tokens"] = feature.max_tokens_per_request
        if feature.max_requests_per_minute:
            applied_constraints["max_rpm"] = feature.max_requests_per_minute
        if feature.max_cost_per_request_usd:
            applied_constraints["max_cost_usd"] = feature.max_cost_per_request_usd
        if feature.require_data_separation:
            applied_constraints["require_data_separation"] = True
        if not feature.allow_pii:
            applied_constraints["pii_blocked"] = True

        return FeatureValidationResult(
            allowed=True,
            feature_id=feature.id,
            feature_name=feature.name,
            decision_code="ALLOWED",
            reason=f"Request allowed for feature '{feature.name}'",
            applied_constraints=applied_constraints,
        )

    def get_feature_constraints(self, app_id: str, feature_id: str) -> Optional[FeatureDefinition]:
        """Récupère les contraintes d'une feature."""
        registry = self._registries.get(app_id)
        if not registry:
            return None
        return registry.features.get(feature_id)

    def list_features(self, app_id: str) -> list[FeatureDefinition]:
        """Liste les features d'une application."""
        registry = self._registries.get(app_id)
        if not registry:
            return []
        return list(registry.features.values())


# Singleton
feature_registry = FeatureRegistry()


async def enforce_feature_async(
    app_id: str,
    feature_id: Optional[str],
    action: FeatureAction,
    model: str,
    environment: str,
    estimated_tokens: Optional[int] = None,
    estimated_cost_usd: Optional[float] = None,
) -> FeatureValidationResult:
    """
    Enforce feature allowlisting (async version - loads from DB).

    Raises:
        FeatureEnforcementError si la requête n'est pas autorisée
    """
    result = await feature_registry.validate_request_async(
        app_id=app_id,
        feature_id=feature_id,
        action=action,
        model=model,
        environment=environment,
        estimated_tokens=estimated_tokens,
        estimated_cost_usd=estimated_cost_usd,
    )

    if not result.allowed:
        raise FeatureEnforcementError(result)

    return result


def enforce_feature(
    app_id: str,
    feature_id: Optional[str],
    action: FeatureAction,
    model: str,
    environment: str,
    estimated_tokens: Optional[int] = None,
    estimated_cost_usd: Optional[float] = None,
) -> FeatureValidationResult:
    """
    Enforce feature allowlisting (sync version - uses cache only).

    Raises:
        FeatureEnforcementError si la requête n'est pas autorisée
    """
    result = feature_registry.validate_request(
        app_id=app_id,
        feature_id=feature_id,
        action=action,
        model=model,
        environment=environment,
        estimated_tokens=estimated_tokens,
        estimated_cost_usd=estimated_cost_usd,
    )

    if not result.allowed:
        raise FeatureEnforcementError(result)

    return result
