"""
Policy Engine - Evaluates policies before LLM calls.

Uses AsyncLoadableEntity for DB loading and ConditionMatcher for rule evaluation.
"""

from pydantic import BaseModel
from typing import Optional
from enum import Enum
import logging

__all__ = [
    "PolicyDecision",
    "PolicyResult",
    "PolicyRule",
    "PolicyEngine",
    "policy_engine",
]

from backend.core.contracts import UsageContract, Environment
from backend.core.auth import AppCredentials
from backend.core.base import (
    AsyncLoadableEntity,
    ConditionMatcher,
    ConditionContext,
)

logger = logging.getLogger(__name__)


class PolicyDecision(str, Enum):
    ALLOW = "allow"
    WARN = "warn"
    DENY = "deny"


class PolicyResult(BaseModel):
    decision: PolicyDecision
    reason: Optional[str] = None
    warnings: list[str] = []
    matched_rules: list[str] = []


class PolicyRule(BaseModel):
    """Règle de policy configurable."""

    name: str
    enabled: bool = True

    # Conditions
    environments: Optional[list[Environment]] = None
    apps: Optional[list[str]] = None  # app_id patterns
    features: Optional[list[str]] = None
    models: Optional[list[str]] = None

    # Limits
    max_tokens: Optional[int] = None
    max_context_tokens: Optional[int] = None
    allowed_hours: Optional[tuple[int, int]] = None  # (start_hour, end_hour)

    # Decision
    action: PolicyDecision = PolicyDecision.ALLOW


class PolicyEngine(AsyncLoadableEntity[list[PolicyRule]]):
    """
    Moteur de policies.
    Évalue les règles AVANT l'appel LLM.

    Inherits from AsyncLoadableEntity for lazy DB loading.
    Uses ConditionMatcher for unified condition evaluation.
    """

    def __init__(self, rules: Optional[list[PolicyRule]] = None):
        super().__init__()
        if rules:
            self._data = rules
            self._loaded = True

    @property
    def rules(self) -> list[PolicyRule]:
        """Get loaded rules."""
        return self._data or []

    @rules.setter
    def rules(self, value: list[PolicyRule]) -> None:
        """Set rules (for backward compatibility)."""
        self._data = value
        self._loaded = True

    def _get_default_value(self) -> list[PolicyRule]:
        """Return empty list on load failure."""
        return []

    async def _load_from_db(self) -> list[PolicyRule]:
        """Load policies from database."""
        from backend.db.session import get_db_context
        from backend.db.models import PolicyRule as DBPolicyRule
        from sqlalchemy import select

        async with get_db_context() as db:
            result = await db.execute(
                select(DBPolicyRule)
                .where(DBPolicyRule.is_enabled.is_(True))
                .order_by(DBPolicyRule.priority.desc())
            )
            db_policies = result.scalars().all()

            rules = []
            for p in db_policies:
                conditions = p.conditions or {}
                rule = PolicyRule(
                    name=p.name,
                    enabled=p.is_enabled,
                    environments=[Environment(e) for e in conditions.get("environments", [])]
                    if conditions.get("environments")
                    else None,
                    features=conditions.get("features"),
                    models=conditions.get("models"),
                    max_tokens=conditions.get("max_tokens"),
                    max_context_tokens=conditions.get("max_context_tokens"),
                    action=PolicyDecision(p.action.value) if p.action else PolicyDecision.ALLOW,
                )
                rules.append(rule)

            logger.debug(f"Loaded {len(rules)} policies from database")
            return rules

    async def evaluate_async(
        self,
        contract: UsageContract,
        credentials: AppCredentials,
        model: str,
        max_tokens: Optional[int] = None,
        input_tokens: Optional[int] = None,
    ) -> PolicyResult:
        """Async version that ensures policies are loaded first."""
        await self.ensure_loaded()
        return self.evaluate(contract, credentials, model, max_tokens, input_tokens)

    def evaluate(
        self,
        contract: UsageContract,
        credentials: AppCredentials,
        model: str,
        max_tokens: Optional[int] = None,
        input_tokens: Optional[int] = None,
    ) -> PolicyResult:
        """Évalue toutes les règles et retourne la décision."""
        warnings = []
        matched_rules = []

        # Build context for condition matching
        context = ConditionContext(
            model=model,
            environment=contract.environment.value
            if hasattr(contract.environment, "value")
            else str(contract.environment),
            feature=contract.feature,
            app_id=contract.app_id,
            input_tokens=input_tokens,
            max_tokens=max_tokens,
        )

        for rule in self.rules:
            if not rule.enabled:
                continue

            # Check if rule applies using ConditionMatcher
            if not self._rule_matches(rule, context):
                continue

            matched_rules.append(rule.name)

            # Check token limits
            if rule.max_tokens and max_tokens and max_tokens > rule.max_tokens:
                if rule.action == PolicyDecision.DENY:
                    return PolicyResult(
                        decision=PolicyDecision.DENY,
                        reason=f"max_tokens ({max_tokens}) exceeds limit ({rule.max_tokens}) - rule: {rule.name}",
                        matched_rules=matched_rules,
                    )
                elif rule.action == PolicyDecision.WARN:
                    warnings.append(
                        f"max_tokens ({max_tokens}) exceeds soft limit ({rule.max_tokens})"
                    )

            # Check allowed hours using ConditionMatcher
            if rule.allowed_hours:
                ok, reason = ConditionMatcher.matches_time(allowed_hours=rule.allowed_hours)
                if not ok:
                    if rule.action == PolicyDecision.DENY:
                        return PolicyResult(
                            decision=PolicyDecision.DENY,
                            reason=f"{reason} - rule: {rule.name}",
                            matched_rules=matched_rules,
                        )

            # Check model whitelist using ConditionMatcher
            if rule.models:
                ok, reason = ConditionMatcher.matches_model(model, allowed=rule.models)
                if not ok:
                    if rule.action == PolicyDecision.DENY:
                        return PolicyResult(
                            decision=PolicyDecision.DENY,
                            reason=f"{reason} - rule: {rule.name}",
                            matched_rules=matched_rules,
                        )

        # Check credentials model restrictions
        if credentials.allowed_models and model not in credentials.allowed_models:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason=f"Model '{model}' not allowed for app '{credentials.app_id}'",
                matched_rules=matched_rules,
            )

        return PolicyResult(
            decision=PolicyDecision.ALLOW,
            warnings=warnings,
            matched_rules=matched_rules,
        )

    def _rule_matches(self, rule: PolicyRule, context: ConditionContext) -> bool:
        """Check if a rule applies using ConditionMatcher."""
        # Check environment
        if rule.environments:
            env_values = [e.value if hasattr(e, "value") else str(e) for e in rule.environments]
            ok, _ = ConditionMatcher.matches_environment(context.environment, allowed=env_values)
            if not ok:
                return False

        # Check app
        if rule.apps:
            ok, _ = ConditionMatcher.matches_app(context.app_id, allowed=rule.apps)
            if not ok:
                return False

        # Check feature
        if rule.features:
            ok, _ = ConditionMatcher.matches_feature(context.feature, allowed=rule.features)
            if not ok:
                return False

        return True


# Singleton
policy_engine = PolicyEngine()
