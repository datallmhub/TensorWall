"""Request Pipeline - Orchestrates all governance checks.

Integrates Decision Engine with all governance components:
- Authentication
- RBAC
- Contracts
- Features
- Policies
- Budgets
- Security

Provides full traceability and explainability for every decision.
"""

from typing import Optional
from dataclasses import dataclass
import time

from backend.core.auth import AppCredentials
from backend.core.contracts import UsageContract
from backend.core.rbac import RBACContext, Permission, rbac_engine
from .decision import (
    DecisionBuilder,
    DecisionSource,
    DecisionType,
    DecisionCodes,
    Decision,
    create_decision,
)
from .policy import policy_engine, PolicyDecision
from .budget import budget_engine
from .security import security_guard, SecurityCheckResult
from .features import feature_engine


@dataclass
class PipelineRequest:
    """Input for the governance pipeline."""

    request_id: str
    credentials: AppCredentials
    contract: UsageContract
    model: str
    messages: list[dict]
    max_tokens: Optional[int] = None
    input_tokens: Optional[int] = None


@dataclass
class PipelineResult:
    """Result from the governance pipeline."""

    allowed: bool
    decision: Decision
    warnings: list[str]
    estimated_cost_usd: float
    security_analysis: Optional[SecurityCheckResult] = None

    def get_security_response(self) -> Optional[dict]:
        """Get security analysis for API response."""
        if self.security_analysis:
            return self.security_analysis.to_api_response()
        return None


class GovernancePipeline:
    """
    Main governance pipeline.

    Orchestrates all checks and produces an explainable decision.
    """

    def __init__(
        self,
        skip_security: bool = False,
        skip_features: bool = False,
        skip_budget: bool = False,
    ):
        self.skip_security = skip_security
        self.skip_features = skip_features
        self.skip_budget = skip_budget
        self._security_analysis: Optional[SecurityCheckResult] = None

    async def evaluate(self, request: PipelineRequest) -> PipelineResult:
        """
        Evaluate a request through the full governance pipeline.

        Order of checks:
        1. RBAC (can this key use LLM API?)
        2. Contract validation
        3. Feature enforcement
        4. Security checks
        5. Policy evaluation
        6. Budget check

        Returns a complete decision with full trace.
        """
        # Reset security analysis for this request
        self._security_analysis = None

        builder = create_decision(request.request_id)
        builder.set_context(
            app_id=request.contract.app_id,
            feature=request.contract.feature,
            environment=request.contract.environment.value,
            model=request.model,
        )

        warnings = []
        estimated_cost = 0.0

        # 1. RBAC Check
        if not self._check_rbac(builder, request):
            return self._build_result(builder, warnings, estimated_cost)

        # 2. Contract validation
        if not self._check_contract(builder, request):
            return self._build_result(builder, warnings, estimated_cost)

        # 3. Feature enforcement
        if not self.skip_features:
            feature_result = self._check_features(builder, request)
            if not feature_result:
                return self._build_result(builder, warnings, estimated_cost)
            if feature_result.get("warnings"):
                warnings.extend(feature_result["warnings"])

        # 4. Security checks
        if not self.skip_security:
            security_result = self._check_security(builder, request)
            if not security_result:
                return self._build_result(builder, warnings, estimated_cost)
            if security_result.get("warnings"):
                warnings.extend(security_result["warnings"])

        # 5. Policy evaluation
        policy_result = self._check_policy(builder, request)
        if not policy_result["allowed"]:
            return self._build_result(builder, warnings, estimated_cost)
        if policy_result.get("warnings"):
            warnings.extend(policy_result["warnings"])

        # 6. Budget check
        if not self.skip_budget:
            budget_result = self._check_budget(builder, request)
            estimated_cost = budget_result.get("estimated_cost", 0.0)
            if not budget_result["allowed"]:
                return self._build_result(builder, warnings, estimated_cost)
            if budget_result.get("warnings"):
                warnings.extend(budget_result["warnings"])

        # All checks passed
        builder.allow()
        return self._build_result(builder, warnings, estimated_cost)

    def _check_rbac(self, builder: DecisionBuilder, request: PipelineRequest) -> bool:
        """Check RBAC permissions."""
        start = time.time()

        # For API key auth, we check if the key can use LLM
        # In full RBAC, we'd have user context
        from backend.core.rbac import Role

        # Get role from credentials or default to SERVICE
        role = getattr(request.credentials, "role", None) or Role.SERVICE

        context = RBACContext(
            role=role,
            app_id=request.credentials.app_id,
        )

        result = rbac_engine.has_permission(
            context,
            Permission.LLM_CHAT,
            resource_app_id=request.contract.app_id,
        )

        duration_ms = (time.time() - start) * 1000

        builder.add_trace(
            source=DecisionSource.AUTHORIZATION,
            checked="llm:chat permission",
            result=DecisionType.ALLOW if result.allowed else DecisionType.DENY,
            matched=not result.allowed,
            condition=f"role={context.role.value}",
            actual_value=context.role.value,
            expected_value="service|developer|admin|owner",
            duration_ms=duration_ms,
        )

        if not result.allowed:
            builder.deny(
                source=DecisionSource.AUTHORIZATION,
                code=DecisionCodes.AUTHZ_PERMISSION_DENIED,
                message=result.reason,
                details={"role": result.role, "permission": result.permission},
            )
            return False

        return True

    def _check_contract(
        self, builder: DecisionBuilder, request: PipelineRequest
    ) -> bool:
        """Validate the usage contract."""
        start = time.time()

        issues = []

        # Check required fields
        if not request.contract.app_id:
            issues.append("app_id is required")
        if not request.contract.feature:
            issues.append("feature is required")
        if not request.contract.environment:
            issues.append("environment is required")

        duration_ms = (time.time() - start) * 1000

        builder.add_trace(
            source=DecisionSource.CONTRACT,
            checked="contract_validation",
            result=DecisionType.ALLOW if not issues else DecisionType.DENY,
            matched=bool(issues),
            condition="required fields present",
            actual_value={
                "app_id": request.contract.app_id,
                "feature": request.contract.feature,
            },
            duration_ms=duration_ms,
        )

        if issues:
            builder.deny(
                source=DecisionSource.CONTRACT,
                code=DecisionCodes.CONTRACT_INCOMPLETE,
                message=f"Contract validation failed: {', '.join(issues)}",
                details={"issues": issues},
            )
            return False

        return True

    def _check_features(
        self, builder: DecisionBuilder, request: PipelineRequest
    ) -> Optional[dict]:
        """Check feature enforcement."""
        start = time.time()

        result = feature_engine.check_feature(
            app_id=request.contract.app_id,
            feature=request.contract.feature,
            action=request.contract.action.value if request.contract.action else None,
            model=request.model,
            environment=request.contract.environment.value,
            output_tokens=request.max_tokens,
        )

        duration_ms = (time.time() - start) * 1000

        builder.add_trace(
            source=DecisionSource.FEATURE,
            checked=f"feature:{request.contract.feature}",
            result=DecisionType.ALLOW if result.allowed else DecisionType.DENY,
            matched=not result.allowed,
            condition=f"feature={request.contract.feature}, model={request.model}",
            actual_value=request.contract.feature,
            duration_ms=duration_ms,
        )

        if not result.allowed:
            builder.deny(
                source=DecisionSource.FEATURE,
                code=DecisionCodes.FEATURE_NOT_ALLOWED,
                message=result.reason,
                details={"feature": result.feature},
            )
            return None

        return {"allowed": True, "warnings": result.warnings}

    def _check_security(
        self, builder: DecisionBuilder, request: PipelineRequest
    ) -> Optional[dict]:
        """Run security checks and store full analysis."""
        start = time.time()
        warnings = []

        # Run full security analysis
        full_result = security_guard.full_analysis(request.messages)

        # Store for inclusion in response (OSS: visible in every request)
        self._security_analysis = full_result

        # Get risk level as string
        risk_level = full_result.risk_level
        if hasattr(risk_level, "value"):
            risk_level = risk_level.value
        risk_level = risk_level or "low"

        builder.add_trace(
            source=DecisionSource.SECURITY,
            checked="security_analysis",
            result=DecisionType.ALLOW,  # OSS: detection only, never blocks
            matched=len(full_result.findings) > 0,
            condition="prompt_injection|secrets|pii",
            actual_value=f"risk_score={full_result.risk_score}, risk_level={risk_level}",
            expected_value="risk_level=low|medium",
            duration_ms=(time.time() - start) * 1000,
        )

        # Add warnings for any findings (detection only, never blocks)
        for finding in full_result.findings:
            builder.warn(
                source=DecisionSource.SECURITY,
                code=DecisionCodes.SECURITY_INVALID_STRUCTURE,  # Generic security warning
                message=finding.description,
            )
            warnings.append(f"[{finding.category}] {finding.description}")

        # Check message structure (separate validation)
        structure_result = security_guard.check_message_structure(request.messages)

        builder.add_trace(
            source=DecisionSource.SECURITY,
            checked="message_structure",
            result=DecisionType.ALLOW if structure_result.safe else DecisionType.WARN,
            matched=not structure_result.safe,
            condition="valid_roles_and_structure",
            duration_ms=(time.time() - start) * 1000,
        )

        if not structure_result.safe:
            # Structure issues are warnings, not blocks (unless critical)
            for issue in structure_result.issues:
                builder.warn(
                    source=DecisionSource.SECURITY,
                    code=DecisionCodes.SECURITY_INVALID_STRUCTURE,
                    message=issue,
                )
                warnings.append(issue)

        return {"allowed": True, "warnings": warnings}

    def _check_policy(self, builder: DecisionBuilder, request: PipelineRequest) -> dict:
        """Evaluate policy rules."""
        start = time.time()

        result = policy_engine.evaluate(
            contract=request.contract,
            credentials=request.credentials,
            model=request.model,
            max_tokens=request.max_tokens,
            input_tokens=request.input_tokens,
        )

        duration_ms = (time.time() - start) * 1000

        # Add trace for each matched rule
        for rule_name in result.matched_rules:
            builder.add_trace(
                source=DecisionSource.POLICY,
                checked=f"rule:{rule_name}",
                result=DecisionType(result.decision.value),
                matched=True,
                rule_name=rule_name,
                condition=f"model={request.model}, max_tokens={request.max_tokens}",
                duration_ms=(
                    duration_ms / len(result.matched_rules)
                    if result.matched_rules
                    else duration_ms
                ),
            )

        if result.decision == PolicyDecision.DENY:
            builder.deny(
                source=DecisionSource.POLICY,
                code=DecisionCodes.POLICY_CUSTOM_RULE,
                message=result.reason,
                details={"matched_rules": result.matched_rules},
            )
            return {"allowed": False}

        warnings = []
        if result.decision == PolicyDecision.WARN:
            for warning in result.warnings:
                builder.warn(
                    source=DecisionSource.POLICY,
                    code=DecisionCodes.POLICY_CUSTOM_RULE,
                    message=warning,
                )
                warnings.append(warning)

        return {"allowed": True, "warnings": warnings}

    def _check_budget(self, builder: DecisionBuilder, request: PipelineRequest) -> dict:
        """Check budget constraints."""
        start = time.time()

        # Estimate input tokens if not provided
        input_tokens = request.input_tokens
        if not input_tokens:
            input_tokens = sum(
                len(m.get("content", "").split()) * 1.3 for m in request.messages
            )

        # Estimate cost
        estimated_cost = budget_engine.estimate_cost(
            model=request.model,
            input_tokens=int(input_tokens),
            output_tokens=request.max_tokens or 500,
        )

        result = budget_engine.check_budget(
            app_id=request.contract.app_id,
            feature=request.contract.feature,
            environment=request.contract.environment.value,
            estimated_cost_usd=estimated_cost,
        )

        duration_ms = (time.time() - start) * 1000

        builder.add_trace(
            source=DecisionSource.BUDGET,
            checked="budget_limit",
            result=DecisionType.ALLOW if result.allowed else DecisionType.DENY,
            matched=not result.allowed,
            condition=f"estimated_cost=${estimated_cost:.4f}",
            actual_value=result.current_spend_usd,
            expected_value=result.limit_usd,
            duration_ms=duration_ms,
        )

        if not result.allowed:
            builder.deny(
                source=DecisionSource.BUDGET,
                code=DecisionCodes.BUDGET_HARD_LIMIT,
                message=result.warning or "Budget exceeded",
                details={
                    "current_spend": result.current_spend_usd,
                    "limit": result.limit_usd,
                    "usage_percent": result.usage_percent,
                },
            )
            return {"allowed": False, "estimated_cost": estimated_cost}

        warnings = []
        if result.warning:
            builder.warn(
                source=DecisionSource.BUDGET,
                code=DecisionCodes.BUDGET_SOFT_LIMIT,
                message=result.warning,
                details={
                    "current_spend": result.current_spend_usd,
                    "limit": result.limit_usd,
                    "usage_percent": result.usage_percent,
                },
            )
            warnings.append(result.warning)

        return {"allowed": True, "warnings": warnings, "estimated_cost": estimated_cost}

    def _build_result(
        self,
        builder: DecisionBuilder,
        warnings: list[str],
        estimated_cost: float,
    ) -> PipelineResult:
        """Build the final pipeline result."""
        decision = builder.build()
        return PipelineResult(
            allowed=decision.allowed,
            decision=decision,
            warnings=warnings,
            estimated_cost_usd=estimated_cost,
            security_analysis=self._security_analysis,
        )


# Singleton instance
governance_pipeline = GovernancePipeline()
