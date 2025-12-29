"""Feature Enforcement Engine.

Enforces strict use-case / feature restrictions per application.
Each application declares allowed features with their constraints.

Uses ConditionMatcher for unified validation logic.
"""

from typing import Optional
from pydantic import BaseModel
from enum import Enum
import logging

from .decision import (
    DecisionBuilder,
    DecisionSource,
    DecisionType,
    DecisionCodes,
)
from backend.core.base import ConditionMatcher

logger = logging.getLogger(__name__)


class FeatureAction(str, Enum):
    """Allowed actions for features."""

    GENERATE = "generate"
    SUMMARIZE = "summarize"
    CLASSIFY = "classify"
    EXTRACT = "extract"
    TRANSLATE = "translate"
    EMBED = "embed"
    CHAT = "chat"
    COMPLETE = "complete"


class FeatureConfig(BaseModel):
    """Configuration for a feature."""

    name: str
    description: Optional[str] = None
    enabled: bool = True

    # Allowed actions for this feature
    allowed_actions: list[FeatureAction] = list(FeatureAction)

    # Model restrictions for this feature
    allowed_models: list[str] = []  # Empty = all allowed
    denied_models: list[str] = []

    # Token limits specific to this feature
    max_input_tokens: Optional[int] = None
    max_output_tokens: Optional[int] = None

    # Environment restrictions
    allowed_environments: list[str] = []  # Empty = all allowed
    denied_environments: list[str] = []

    # Output constraints
    require_json_output: bool = False
    json_schema: Optional[dict] = None  # JSON schema for output validation

    # Rate limits specific to this feature
    rate_limit_per_minute: Optional[int] = None
    rate_limit_per_hour: Optional[int] = None

    # Cost controls
    max_cost_per_request_usd: Optional[float] = None


class FeatureRegistry(BaseModel):
    """Registry of allowed features for an application."""

    app_id: str

    # Strict mode: only declared features allowed
    strict_mode: bool = True

    # Default feature (used when none specified)
    default_feature: Optional[str] = None

    # Registered features
    features: dict[str, FeatureConfig] = {}

    # Global model restrictions (apply to all features)
    global_allowed_models: list[str] = []
    global_denied_models: list[str] = []


class FeatureCheckResult(BaseModel):
    """Result of feature check."""

    allowed: bool
    feature: str
    reason: Optional[str] = None
    warnings: list[str] = []
    config: Optional[FeatureConfig] = None


class FeatureEngine:
    """
    Feature Enforcement Engine.

    Validates that requests match declared features and their constraints.
    """

    def __init__(self):
        # In-memory registry (TODO: load from DB)
        self.registries: dict[str, FeatureRegistry] = {}

    def register_app(self, registry: FeatureRegistry) -> None:
        """Register an application's feature configuration."""
        self.registries[registry.app_id] = registry

    def get_registry(self, app_id: str) -> Optional[FeatureRegistry]:
        """Get feature registry for an application."""
        return self.registries.get(app_id)

    def add_feature(self, app_id: str, config: FeatureConfig) -> None:
        """Add or update a feature for an application."""
        if app_id not in self.registries:
            self.registries[app_id] = FeatureRegistry(app_id=app_id)
        self.registries[app_id].features[config.name] = config

    def remove_feature(self, app_id: str, feature_name: str) -> bool:
        """Remove a feature from an application."""
        if app_id in self.registries:
            if feature_name in self.registries[app_id].features:
                del self.registries[app_id].features[feature_name]
                return True
        return False

    def check_feature(
        self,
        app_id: str,
        feature: str,
        action: Optional[str] = None,
        model: Optional[str] = None,
        environment: Optional[str] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
    ) -> FeatureCheckResult:
        """
        Check if a feature request is allowed.

        Args:
            app_id: Application ID
            feature: Feature name
            action: Action type (generate, summarize, etc.)
            model: Model being requested
            environment: Environment (dev, staging, prod)
            input_tokens: Estimated input tokens
            output_tokens: Max output tokens requested

        Returns:
            FeatureCheckResult with allowed status and details
        """
        registry = self.registries.get(app_id)

        # No registry = no restrictions (non-strict mode by default)
        if not registry:
            return FeatureCheckResult(
                allowed=True,
                feature=feature,
                warnings=["No feature registry configured for this app"],
            )

        # Use default feature if none specified
        effective_feature = feature or registry.default_feature
        if not effective_feature:
            if registry.strict_mode:
                return FeatureCheckResult(
                    allowed=False,
                    feature=feature or "unknown",
                    reason="No feature specified and no default configured (strict mode)",
                )
            return FeatureCheckResult(
                allowed=True,
                feature="default",
                warnings=["No feature specified, using permissive default"],
            )

        # Check if feature exists
        config = registry.features.get(effective_feature)
        if not config:
            if registry.strict_mode:
                return FeatureCheckResult(
                    allowed=False,
                    feature=effective_feature,
                    reason=f"Feature '{effective_feature}' not registered (strict mode)",
                )
            return FeatureCheckResult(
                allowed=True,
                feature=effective_feature,
                warnings=[f"Feature '{effective_feature}' not registered"],
            )

        # Check if feature is enabled
        if not config.enabled:
            return FeatureCheckResult(
                allowed=False,
                feature=effective_feature,
                reason=f"Feature '{effective_feature}' is disabled",
                config=config,
            )

        warnings = []

        # Check action
        if action:
            try:
                action_enum = FeatureAction(action)
                if action_enum not in config.allowed_actions:
                    return FeatureCheckResult(
                        allowed=False,
                        feature=effective_feature,
                        reason=f"Action '{action}' not allowed for feature '{effective_feature}'",
                        config=config,
                    )
            except ValueError:
                warnings.append(f"Unknown action '{action}'")

        # Check model restrictions using ConditionMatcher
        if model:
            # Global restrictions first
            ok, reason = ConditionMatcher.matches_model(
                model,
                allowed=registry.global_allowed_models or None,
                denied=registry.global_denied_models or None,
            )
            if not ok:
                return FeatureCheckResult(
                    allowed=False,
                    feature=effective_feature,
                    reason=reason or f"Model '{model}' not allowed globally",
                    config=config,
                )

            # Feature-specific restrictions
            ok, reason = ConditionMatcher.matches_model(
                model,
                allowed=config.allowed_models or None,
                denied=config.denied_models or None,
            )
            if not ok:
                return FeatureCheckResult(
                    allowed=False,
                    feature=effective_feature,
                    reason=reason
                    or f"Model '{model}' not allowed for feature '{effective_feature}'",
                    config=config,
                )

        # Check environment restrictions using ConditionMatcher
        if environment:
            ok, reason = ConditionMatcher.matches_environment(
                environment,
                allowed=config.allowed_environments or None,
                denied=config.denied_environments or None,
            )
            if not ok:
                return FeatureCheckResult(
                    allowed=False,
                    feature=effective_feature,
                    reason=reason
                    or f"Environment '{environment}' not allowed for feature '{effective_feature}'",
                    config=config,
                )

        # Check token limits using ConditionMatcher
        ok, reason = ConditionMatcher.matches_tokens(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            max_input=config.max_input_tokens,
            max_output=config.max_output_tokens,
        )
        if not ok:
            return FeatureCheckResult(
                allowed=False,
                feature=effective_feature,
                reason=reason or f"Token limit exceeded for feature '{effective_feature}'",
                config=config,
            )

        return FeatureCheckResult(
            allowed=True,
            feature=effective_feature,
            warnings=warnings if warnings else None,
            config=config,
        )

    def check_feature_with_decision(
        self,
        builder: DecisionBuilder,
        app_id: str,
        feature: str,
        **kwargs,
    ) -> FeatureCheckResult:
        """
        Check feature and add to decision builder.

        Integrates with the Decision Engine for full traceability.
        """
        import time

        start = time.time()

        result = self.check_feature(app_id, feature, **kwargs)

        duration_ms = (time.time() - start) * 1000

        # Add trace
        builder.add_trace(
            source=DecisionSource.FEATURE,
            checked=f"feature:{feature}",
            result=DecisionType.ALLOW if result.allowed else DecisionType.DENY,
            matched=not result.allowed,
            condition=f"app={app_id}, feature={feature}",
            actual_value=feature,
            expected_value=list(
                self.registries.get(app_id, FeatureRegistry(app_id=app_id)).features.keys()
            ),
            duration_ms=duration_ms,
        )

        # Add to decision
        if not result.allowed:
            builder.deny(
                source=DecisionSource.FEATURE,
                code=DecisionCodes.FEATURE_NOT_ALLOWED,
                message=result.reason,
                details={
                    "feature": result.feature,
                    "app_id": app_id,
                },
            )

        # Add warnings
        for warning in result.warnings or []:
            builder.warn(
                source=DecisionSource.FEATURE,
                code=DecisionCodes.FEATURE_UNKNOWN,
                message=warning,
            )

        return result

    def list_features(self, app_id: str) -> list[FeatureConfig]:
        """List all features for an application."""
        registry = self.registries.get(app_id)
        if not registry:
            return []
        return list(registry.features.values())


# Singleton instance
feature_engine = FeatureEngine()


# Helper to create a default feature registry for testing
def create_default_registry(app_id: str) -> FeatureRegistry:
    """Create a default feature registry with common features."""
    return FeatureRegistry(
        app_id=app_id,
        strict_mode=False,
        default_feature="general",
        features={
            "general": FeatureConfig(
                name="general",
                description="General purpose LLM usage",
                allowed_actions=list(FeatureAction),
            ),
            "chat": FeatureConfig(
                name="chat",
                description="Conversational chat",
                allowed_actions=[FeatureAction.CHAT, FeatureAction.GENERATE],
            ),
            "summarization": FeatureConfig(
                name="summarization",
                description="Text summarization",
                allowed_actions=[FeatureAction.SUMMARIZE],
                max_output_tokens=1000,
            ),
            "classification": FeatureConfig(
                name="classification",
                description="Text classification",
                allowed_actions=[FeatureAction.CLASSIFY],
                require_json_output=True,
                max_output_tokens=100,
            ),
            "extraction": FeatureConfig(
                name="extraction",
                description="Information extraction",
                allowed_actions=[FeatureAction.EXTRACT],
                require_json_output=True,
            ),
        },
    )
