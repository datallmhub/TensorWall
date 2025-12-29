"""InMemory Feature Adapter - Implémentation pour les tests.

Architecture Hexagonale: Adapter natif qui implémente directement
l'interface FeatureRegistryPort sans dépendre de la base de données.
Utile pour les tests unitaires et d'intégration.
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from backend.ports.feature_registry import (
    FeatureRegistryPort,
    FeatureDefinition,
    FeatureCheckResult,
    FeatureAction,
    FeatureDecision,
)


@dataclass
class AppConfig:
    """Configuration d'une application."""

    strict_mode: bool = True
    default_feature_id: Optional[str] = None


class InMemoryFeatureAdapter(FeatureRegistryPort):
    """Adapter en mémoire pour le registre de features.

    Implémentation sans base de données pour les tests.
    Stocke tout en mémoire.
    """

    def __init__(self, default_strict_mode: bool = True):
        """Initialise l'adapter.

        Args:
            default_strict_mode: Mode strict par défaut pour nouvelles apps
        """
        self.default_strict_mode = default_strict_mode
        self._features: dict[str, dict[str, FeatureDefinition]] = defaultdict(dict)
        self._app_configs: dict[str, AppConfig] = {}

    def _get_app_config(self, app_id: str) -> AppConfig:
        """Récupère ou crée la config d'une application."""
        if app_id not in self._app_configs:
            self._app_configs[app_id] = AppConfig(strict_mode=self.default_strict_mode)
        return self._app_configs[app_id]

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
        """Vérifie si une requête est autorisée pour une feature."""
        config = self._get_app_config(app_id)
        app_features = self._features.get(app_id, {})

        # Si pas de features enregistrées, mode permissif
        if not app_features:
            return FeatureCheckResult(
                allowed=True,
                decision=FeatureDecision.ALLOWED_NO_REGISTRY,
                reason=f"Application {app_id} has no feature registry (permissive mode)",
            )

        # Résoudre la feature
        resolved_feature_id = feature_id or config.default_feature_id

        if not resolved_feature_id:
            if config.strict_mode:
                return FeatureCheckResult(
                    allowed=False,
                    decision=FeatureDecision.DENIED_NO_FEATURE_SPECIFIED,
                    reason="No feature specified and no default feature configured (strict mode)",
                )
            else:
                return FeatureCheckResult(
                    allowed=True,
                    decision=FeatureDecision.ALLOWED_PERMISSIVE,
                    reason="No feature specified but strict mode is disabled",
                )

        # Vérifier si la feature existe
        feature = app_features.get(resolved_feature_id)

        if not feature:
            if config.strict_mode:
                return FeatureCheckResult(
                    allowed=False,
                    decision=FeatureDecision.DENIED_UNKNOWN_FEATURE,
                    reason=f"Feature '{resolved_feature_id}' is not registered for application {app_id}",
                    feature_id=resolved_feature_id,
                )
            else:
                return FeatureCheckResult(
                    allowed=True,
                    decision=FeatureDecision.ALLOWED_PERMISSIVE,
                    reason=f"Feature '{resolved_feature_id}' unknown but strict mode disabled",
                    feature_id=resolved_feature_id,
                )

        # Vérifier si active
        if not feature.is_active:
            return FeatureCheckResult(
                allowed=False,
                decision=FeatureDecision.DENIED_FEATURE_DISABLED,
                reason=f"Feature '{feature.name}' is currently disabled",
                feature_id=feature.id,
                feature_name=feature.name,
            )

        # Vérifier l'action
        if feature.allowed_actions and action not in feature.allowed_actions:
            return FeatureCheckResult(
                allowed=False,
                decision=FeatureDecision.DENIED_ACTION_NOT_ALLOWED,
                reason=f"Action '{action.value}' is not allowed for feature '{feature.name}'. Allowed: {[a.value for a in feature.allowed_actions]}",
                feature_id=feature.id,
                feature_name=feature.name,
            )

        # Vérifier le modèle
        if feature.allowed_models and not self._model_matches(model, feature.allowed_models):
            return FeatureCheckResult(
                allowed=False,
                decision=FeatureDecision.DENIED_MODEL_NOT_ALLOWED,
                reason=f"Model '{model}' is not allowed for feature '{feature.name}'. Allowed: {feature.allowed_models}",
                feature_id=feature.id,
                feature_name=feature.name,
            )

        # Vérifier l'environnement
        if feature.allowed_environments and environment not in feature.allowed_environments:
            return FeatureCheckResult(
                allowed=False,
                decision=FeatureDecision.DENIED_ENVIRONMENT_NOT_ALLOWED,
                reason=f"Environment '{environment}' is not allowed for feature '{feature.name}'. Allowed: {feature.allowed_environments}",
                feature_id=feature.id,
                feature_name=feature.name,
            )

        # Vérifier les tokens
        if feature.max_tokens_per_request and estimated_tokens:
            if estimated_tokens > feature.max_tokens_per_request:
                return FeatureCheckResult(
                    allowed=False,
                    decision=FeatureDecision.DENIED_TOKEN_LIMIT,
                    reason=f"Estimated tokens ({estimated_tokens}) exceeds limit ({feature.max_tokens_per_request})",
                    feature_id=feature.id,
                    feature_name=feature.name,
                )

        # Vérifier le coût
        if feature.max_cost_per_request_usd and estimated_cost_usd:
            if estimated_cost_usd > feature.max_cost_per_request_usd:
                return FeatureCheckResult(
                    allowed=False,
                    decision=FeatureDecision.DENIED_COST_LIMIT,
                    reason=f"Estimated cost (${estimated_cost_usd:.4f}) exceeds limit (${feature.max_cost_per_request_usd:.4f})",
                    feature_id=feature.id,
                    feature_name=feature.name,
                )

        # Tout OK - construire les contraintes appliquées
        applied_constraints = {}
        if feature.max_tokens_per_request:
            applied_constraints["max_tokens"] = feature.max_tokens_per_request
        if feature.max_cost_per_request_usd:
            applied_constraints["max_cost_usd"] = feature.max_cost_per_request_usd
        if feature.max_requests_per_minute:
            applied_constraints["max_rpm"] = feature.max_requests_per_minute
        if feature.require_data_separation:
            applied_constraints["require_data_separation"] = True
        if not feature.allow_pii:
            applied_constraints["pii_blocked"] = True

        return FeatureCheckResult(
            allowed=True,
            decision=FeatureDecision.ALLOWED,
            reason=f"Request allowed for feature '{feature.name}'",
            feature_id=feature.id,
            feature_name=feature.name,
            applied_constraints=applied_constraints,
        )

    def _model_matches(self, model: str, allowed_models: list[str]) -> bool:
        """Vérifie si un modèle correspond à la liste autorisée.

        Supporte les wildcards simples (ex: "gpt-*").
        """
        model_lower = model.lower()
        for allowed in allowed_models:
            allowed_lower = allowed.lower()
            if allowed_lower.endswith("*"):
                # Wildcard match
                prefix = allowed_lower[:-1]
                if model_lower.startswith(prefix):
                    return True
            elif model_lower == allowed_lower:
                return True
        return False

    async def register_feature(
        self,
        app_id: str,
        feature: FeatureDefinition,
    ) -> None:
        """Enregistre une feature pour une application."""
        self._features[app_id][feature.id] = feature

    async def remove_feature(
        self,
        app_id: str,
        feature_id: str,
    ) -> bool:
        """Retire une feature du registre."""
        if app_id in self._features and feature_id in self._features[app_id]:
            del self._features[app_id][feature_id]
            return True
        return False

    async def get_feature(
        self,
        app_id: str,
        feature_id: str,
    ) -> Optional[FeatureDefinition]:
        """Récupère la définition d'une feature."""
        return self._features.get(app_id, {}).get(feature_id)

    async def list_features(
        self,
        app_id: str,
    ) -> list[FeatureDefinition]:
        """Liste les features d'une application."""
        return list(self._features.get(app_id, {}).values())

    async def set_strict_mode(
        self,
        app_id: str,
        strict: bool,
    ) -> None:
        """Configure le mode strict pour une application."""
        config = self._get_app_config(app_id)
        config.strict_mode = strict

    async def set_default_feature(
        self,
        app_id: str,
        feature_id: Optional[str],
    ) -> None:
        """Configure la feature par défaut pour une application."""
        config = self._get_app_config(app_id)
        config.default_feature_id = feature_id

    # Test helpers
    def clear_all(self) -> None:
        """Efface toutes les données (pour les tests)."""
        self._features.clear()
        self._app_configs.clear()

    def get_feature_count(self, app_id: str) -> int:
        """Retourne le nombre de features enregistrées."""
        return len(self._features.get(app_id, {}))

    def is_strict_mode(self, app_id: str) -> bool:
        """Vérifie si le mode strict est activé."""
        return self._get_app_config(app_id).strict_mode
