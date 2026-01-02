"""
Policy Simulation / Dry-Run Mode.

Permet de simuler l'exécution d'une requête sans l'effectuer réellement,
pour voir quelles policies seraient appliquées et quel serait le résultat.

Uses AsyncLoadableEntity for DB loading and ConditionMatcher for evaluation.
"""

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
import logging

__all__ = [
    "DryRunMode",
    "PolicyImpact",
    "DryRunResult",
    "PolicySimulator",
    "simulate_request",
]

from backend.core.decisions import (
    DecisionChain,
    Decision,
    DecisionStage,
    DecisionOutcome,
    DecisionCode,
)
from backend.core.base import (
    AsyncLoadableEntity,
    ConditionMatcher,
    ConditionMatchResult,
)

logger = logging.getLogger(__name__)


class DryRunMode(str, Enum):
    """Modes de dry-run."""

    FULL = "full"  # Simulate entire pipeline
    POLICIES_ONLY = "policies_only"  # Only check policies
    BUDGET_ONLY = "budget_only"  # Only check budget
    SECURITY_ONLY = "security_only"  # Only check security


class PolicyImpact(BaseModel):
    """Impact d'une policy sur la requête."""

    policy_id: str
    policy_name: str
    would_match: bool
    action: str  # allow, warn, deny
    reason: str
    priority: int
    conditions_matched: list[str] = []
    conditions_failed: list[str] = []


class DryRunResult(BaseModel):
    """Résultat d'une simulation dry-run."""

    # Request info
    request_id: str
    app_id: str
    model: str
    environment: str
    feature_id: Optional[str] = None

    # Simulation mode
    mode: DryRunMode
    simulated_at: datetime = Field(default_factory=datetime.utcnow)

    # Final outcome
    would_be_allowed: bool
    blocking_reason: Optional[str] = None

    # Decision chain
    decision_chain: DecisionChain

    # Policy impacts
    policies_evaluated: list[PolicyImpact] = []
    policies_that_would_block: list[PolicyImpact] = []
    policies_that_would_warn: list[PolicyImpact] = []

    # Budget impact
    budget_impact: Optional[dict] = None

    # Security findings
    security_findings: list[dict] = []

    # Feature validation
    feature_validation: Optional[dict] = None

    # Recommendations
    recommendations: list[str] = []

    def to_summary(self) -> dict:
        """Résumé pour affichage."""
        return {
            "would_be_allowed": self.would_be_allowed,
            "blocking_reason": self.blocking_reason,
            "policies_evaluated": len(self.policies_evaluated),
            "policies_blocking": len(self.policies_that_would_block),
            "policies_warning": len(self.policies_that_would_warn),
            "recommendations": self.recommendations,
        }


class PolicySimulator(AsyncLoadableEntity[list[dict]]):
    """
    Simulateur de policies.

    Permet de tester l'impact de policies existantes ou nouvelles
    sur des requêtes réelles ou hypothétiques.

    Inherits from AsyncLoadableEntity for lazy DB loading.
    Uses ConditionMatcher for unified condition evaluation.
    """

    def __init__(self):
        super().__init__()

    @property
    def policies(self) -> list[dict]:
        """Get loaded policies."""
        return self._data or []

    def _get_default_value(self) -> list[dict]:
        """Return empty list on load failure."""
        return []

    async def _load_from_db(self) -> list[dict]:
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

            policies = []
            for p in db_policies:
                policy = {
                    "id": str(p.uuid),
                    "name": p.name,
                    "rule_type": "policy",
                    "conditions": p.conditions or {},
                    "action": p.action.value if p.action else "allow",
                    "priority": p.priority,
                    "enabled": p.is_enabled,
                }
                policies.append(policy)

            logger.debug(f"Loaded {len(policies)} policies for simulation")
            return policies

    def evaluate_policy(
        self,
        policy: dict,
        model: str,
        environment: str,
        max_tokens: int,
        app_id: str,
    ) -> PolicyImpact:
        """Évalue une policy contre une requête using ConditionMatcher."""
        conditions = policy.get("conditions", {})
        result = ConditionMatchResult()

        # Check model using ConditionMatcher
        if "models" in conditions:
            ok, reason = ConditionMatcher.matches_model(
                model, allowed=conditions["models"]
            )
            if ok:
                result.add_match(f"model={model}")
            else:
                result.add_failure(
                    "model", reason or f"model not in {conditions['models']}"
                )

        # Check environment using ConditionMatcher
        if "environment" in conditions:
            ok, reason = ConditionMatcher.matches_environment(
                environment, allowed=[conditions["environment"]]
            )
            if ok:
                result.add_match(f"environment={environment}")
            else:
                result.add_failure(
                    "environment",
                    reason or f"environment != {conditions['environment']}",
                )

        if "environments" in conditions:
            ok, reason = ConditionMatcher.matches_environment(
                environment, allowed=conditions["environments"]
            )
            if ok:
                result.add_match(f"environment={environment}")
            else:
                result.add_failure(
                    "environment",
                    reason or f"environment not in {conditions['environments']}",
                )

        # Check token limit using ConditionMatcher
        if "max_tokens" in conditions:
            limit = conditions["max_tokens"]
            ok, reason = ConditionMatcher.matches_tokens(
                output_tokens=max_tokens,
                max_output=limit,
            )
            if not ok:
                # Token limit exceeded = policy matches (it's a restriction)
                result.add_match(f"max_tokens={max_tokens} > {limit}")
            else:
                result.add_failure("max_tokens", f"max_tokens={max_tokens} <= {limit}")

        # Check app_id using ConditionMatcher
        if "app_id" in conditions:
            ok, reason = ConditionMatcher.matches_app(
                app_id, allowed=[conditions["app_id"]]
            )
            if ok:
                result.add_match(f"app_id={app_id}")
            else:
                result.add_failure(
                    "app_id", reason or f"app_id != {conditions['app_id']}"
                )

        would_match = result.matches and policy.get("enabled", True)

        return PolicyImpact(
            policy_id=policy["id"],
            policy_name=policy["name"],
            would_match=would_match,
            action=policy["action"],
            reason=f"Policy '{policy['name']}' would {'match' if would_match else 'not match'}",
            priority=policy["priority"],
            conditions_matched=result.matched_conditions,
            conditions_failed=result.failed_conditions,
        )

    async def simulate_policies(
        self,
        model: str,
        environment: str,
        max_tokens: int,
        app_id: str,
        additional_policies: Optional[list[dict]] = None,
    ) -> list[PolicyImpact]:
        """Simule toutes les policies (loads from DB first)."""
        await self.ensure_loaded()

        all_policies = self.policies.copy()
        if additional_policies:
            all_policies.extend(additional_policies)

        # Sort by priority (higher first)
        all_policies.sort(key=lambda p: p.get("priority", 0), reverse=True)

        impacts = []
        for policy in all_policies:
            impact = self.evaluate_policy(
                policy, model, environment, max_tokens, app_id
            )
            impacts.append(impact)

        return impacts


class DryRunEngine:
    """
    Moteur de dry-run complet.

    Simule l'ensemble du pipeline de gouvernance sans effectuer
    l'appel LLM réel.
    """

    def __init__(self):
        self.policy_simulator = PolicySimulator()

    async def simulate(
        self,
        app_id: str,
        model: str,
        environment: str,
        messages: list[dict],
        max_tokens: int = 1000,
        feature_id: Optional[str] = None,
        mode: DryRunMode = DryRunMode.FULL,
        additional_policies: Optional[list[dict]] = None,
    ) -> DryRunResult:
        """
        Simule une requête complète.

        Args:
            app_id: Application ID
            model: Model to simulate
            environment: Environment
            messages: Request messages
            max_tokens: Max output tokens
            feature_id: Feature ID if applicable
            mode: Simulation mode
            additional_policies: Extra policies to test

        Returns:
            DryRunResult with full simulation details
        """
        import uuid

        request_id = str(uuid.uuid4())

        # Initialize decision chain
        chain = DecisionChain(
            request_id=request_id,
            app_id=app_id,
            feature_id=feature_id,
            model=model,
            environment=environment,
        )

        result = DryRunResult(
            request_id=request_id,
            app_id=app_id,
            model=model,
            environment=environment,
            feature_id=feature_id,
            mode=mode,
            would_be_allowed=True,
            decision_chain=chain,
        )

        # 1. Simulate feature validation
        if mode in (DryRunMode.FULL,):
            feature_result = self._simulate_feature_check(
                app_id, feature_id, model, environment
            )
            result.feature_validation = feature_result
            if not feature_result.get("allowed", True):
                chain.add_decision(
                    Decision(
                        stage=DecisionStage.FEATURE_CHECK,
                        outcome=DecisionOutcome.DENY,
                        code=DecisionCode.FEATURE_UNKNOWN,
                        reason=feature_result.get(
                            "reason", "Feature validation failed"
                        ),
                    )
                )
                result.would_be_allowed = False
                result.blocking_reason = feature_result.get("reason")

        # 2. Simulate policies
        if mode in (DryRunMode.FULL, DryRunMode.POLICIES_ONLY):
            policy_impacts = await self.policy_simulator.simulate_policies(
                model=model,
                environment=environment,
                max_tokens=max_tokens,
                app_id=app_id,
                additional_policies=additional_policies,
            )
            result.policies_evaluated = policy_impacts

            for impact in policy_impacts:
                if impact.would_match:
                    if impact.action == "deny":
                        result.policies_that_would_block.append(impact)
                        if result.would_be_allowed:  # First blocking policy
                            result.would_be_allowed = False
                            result.blocking_reason = (
                                f"Policy '{impact.policy_name}': {impact.reason}"
                            )
                            chain.add_decision(
                                Decision(
                                    stage=DecisionStage.POLICY_CHECK,
                                    outcome=DecisionOutcome.DENY,
                                    code=DecisionCode.POLICY_MODEL_BLOCKED,
                                    reason=impact.reason,
                                    policy_id=impact.policy_id,
                                )
                            )
                    elif impact.action == "warn":
                        result.policies_that_would_warn.append(impact)
                        chain.add_decision(
                            Decision(
                                stage=DecisionStage.POLICY_CHECK,
                                outcome=DecisionOutcome.WARN,
                                code=DecisionCode.POLICY_ALLOWED,
                                reason=impact.reason,
                                policy_id=impact.policy_id,
                            )
                        )

        # 3. Simulate budget check
        if mode in (DryRunMode.FULL, DryRunMode.BUDGET_ONLY):
            budget_result = self._simulate_budget_check(
                app_id, environment, model, max_tokens
            )
            result.budget_impact = budget_result

            if not budget_result.get("allowed", True):
                result.would_be_allowed = False
                result.blocking_reason = budget_result.get("reason", "Budget exceeded")
                chain.add_decision(
                    Decision(
                        stage=DecisionStage.BUDGET_CHECK,
                        outcome=DecisionOutcome.DENY,
                        code=DecisionCode.BUDGET_EXCEEDED,
                        reason=budget_result.get("reason", "Budget would be exceeded"),
                    )
                )

        # 4. Simulate security checks
        if mode in (DryRunMode.FULL, DryRunMode.SECURITY_ONLY):
            security_results = self._simulate_security_check(messages)
            result.security_findings = security_results

            for finding in security_results:
                if finding.get("severity") == "high":
                    result.would_be_allowed = False
                    result.blocking_reason = finding.get(
                        "message", "Security violation"
                    )
                    chain.add_decision(
                        Decision(
                            stage=DecisionStage.SECURITY_CHECK,
                            outcome=DecisionOutcome.DENY,
                            code=DecisionCode.SECURITY_INJECTION_DETECTED,
                            reason=finding.get("message"),
                        )
                    )
                    break

        # Generate recommendations
        result.recommendations = self._generate_recommendations(result)

        # Complete chain
        chain.complete(
            DecisionOutcome.ALLOW if result.would_be_allowed else DecisionOutcome.DENY
        )

        return result

    def _simulate_feature_check(
        self,
        app_id: str,
        feature_id: Optional[str],
        model: str,
        environment: str,
    ) -> dict:
        """Simulate feature validation."""
        # Simplified - in real implementation, use feature_registry
        return {
            "allowed": True,
            "feature_id": feature_id,
            "reason": "Feature check passed (simulated)",
        }

    def _simulate_budget_check(
        self,
        app_id: str,
        environment: str,
        model: str,
        max_tokens: int,
    ) -> dict:
        """Simulate budget check."""
        # Simplified estimation
        from backend.application.engines.budget import budget_engine

        estimated_cost = budget_engine.estimate_cost(model, 500, max_tokens)

        return {
            "allowed": True,
            "estimated_cost_usd": estimated_cost,
            "current_spend_usd": 0,
            "remaining_usd": float("inf"),
            "reason": f"Budget check passed (estimated cost: ${estimated_cost:.4f})",
        }

    def _simulate_security_check(self, messages: list[dict]) -> list[dict]:
        """Simulate security checks."""
        findings = []

        for i, msg in enumerate(messages):
            content = msg.get("content", "").lower()

            # Simple injection detection
            if "ignore" in content and "instruction" in content:
                findings.append(
                    {
                        "type": "injection_attempt",
                        "severity": "high",
                        "message": f"Potential injection in message {i}",
                        "message_index": i,
                    }
                )

            # PII detection (simplified)
            if "@" in content and "." in content:
                findings.append(
                    {
                        "type": "potential_pii",
                        "severity": "medium",
                        "message": f"Potential email address in message {i}",
                        "message_index": i,
                    }
                )

        return findings

    def _generate_recommendations(self, result: DryRunResult) -> list[str]:
        """Generate recommendations based on simulation."""
        recommendations = []

        if result.policies_that_would_block:
            policies = [p.policy_name for p in result.policies_that_would_block]
            recommendations.append(
                f"Request would be blocked by {len(policies)} policy(ies): {', '.join(policies)}"
            )

        if result.policies_that_would_warn:
            recommendations.append(
                f"{len(result.policies_that_would_warn)} warning(s) would be triggered"
            )

        if result.security_findings:
            high_severity = [
                f for f in result.security_findings if f.get("severity") == "high"
            ]
            if high_severity:
                recommendations.append(
                    f"Security: {len(high_severity)} high-severity finding(s) detected"
                )

        if not recommendations:
            recommendations.append("Request would proceed without issues")

        return recommendations

    async def test_new_policy(
        self,
        new_policy: dict,
        test_requests: list[dict],
    ) -> list[dict]:
        """
        Test impact of a new policy on historical/test requests.

        Args:
            new_policy: Policy definition to test
            test_requests: List of test requests

        Returns:
            List of impact results for each request
        """
        results = []

        for request in test_requests:
            # Simulate with current policies
            baseline = await self.simulate(
                app_id=request.get("app_id", "test"),
                model=request.get("model", "gpt-4o"),
                environment=request.get("environment", "production"),
                messages=request.get("messages", []),
                max_tokens=request.get("max_tokens", 1000),
                mode=DryRunMode.POLICIES_ONLY,
            )

            # Simulate with new policy added
            with_new = await self.simulate(
                app_id=request.get("app_id", "test"),
                model=request.get("model", "gpt-4o"),
                environment=request.get("environment", "production"),
                messages=request.get("messages", []),
                max_tokens=request.get("max_tokens", 1000),
                mode=DryRunMode.POLICIES_ONLY,
                additional_policies=[new_policy],
            )

            results.append(
                {
                    "request": request,
                    "baseline_allowed": baseline.would_be_allowed,
                    "with_new_policy_allowed": with_new.would_be_allowed,
                    "would_break": baseline.would_be_allowed
                    and not with_new.would_be_allowed,
                    "new_policy_impact": self.policy_simulator.evaluate_policy(
                        new_policy,
                        request.get("model", "gpt-4o"),
                        request.get("environment", "production"),
                        request.get("max_tokens", 1000),
                        request.get("app_id", "test"),
                    ),
                }
            )

        return results


# Singleton
dry_run_engine = DryRunEngine()


async def simulate_request(
    app_id: str,
    model: str,
    environment: str,
    messages: list[dict],
    max_tokens: int = 1000,
    feature_id: Optional[str] = None,
    mode: DryRunMode = DryRunMode.FULL,
) -> DryRunResult:
    """
    Simulate a request through the governance pipeline.

    Use X-Dry-Run: true header to trigger this.
    """
    return await dry_run_engine.simulate(
        app_id=app_id,
        model=model,
        environment=environment,
        messages=messages,
        max_tokens=max_tokens,
        feature_id=feature_id,
        mode=mode,
    )
