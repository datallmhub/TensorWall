"""Decision Engine - Explainable decision making for LLM requests.

Aggregates decisions from Policy, Budget, Security engines and provides
clear, structured explanations for each decision.
"""

from dataclasses import field
from datetime import datetime
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel
import uuid


class DecisionType(str, Enum):
    """Type of decision."""

    ALLOW = "allow"
    WARN = "warn"
    DENY = "deny"
    BLOCK = "block"  # Security block


class DecisionSource(str, Enum):
    """Source of the decision."""

    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    CONTRACT = "contract"
    POLICY = "policy"
    BUDGET = "budget"
    SECURITY = "security"
    RATE_LIMIT = "rate_limit"
    FEATURE = "feature"


class DecisionReason(BaseModel):
    """Detailed reason for a decision."""

    source: DecisionSource
    code: str  # Machine-readable code
    message: str  # Human-readable message
    details: dict[str, Any] = {}  # Additional context
    rule_id: Optional[str] = None  # ID of the rule that triggered
    rule_name: Optional[str] = None  # Name of the rule


class DecisionTrace(BaseModel):
    """
    Trace of a single decision evaluation.

    Captures what was checked, what matched, and the result.
    """

    source: DecisionSource
    checked: str  # What was checked (e.g., "model_whitelist", "budget_limit")
    result: DecisionType
    matched: bool  # Whether a rule matched
    rule_id: Optional[str] = None
    rule_name: Optional[str] = None
    condition: Optional[str] = None  # The condition that was evaluated
    actual_value: Optional[Any] = None  # The actual value found
    expected_value: Optional[Any] = None  # The expected/limit value
    duration_ms: Optional[float] = None


class Decision(BaseModel):
    """
    Complete decision result with full explainability.

    This is the main output of the Decision Engine.
    """

    # Identifiers
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Final decision
    decision: DecisionType
    allowed: bool

    # Primary reason (most important)
    primary_reason: Optional[DecisionReason] = None

    # All reasons (for multi-factor decisions)
    reasons: list[DecisionReason] = []

    # Warnings (things that didn't block but should be noted)
    warnings: list[DecisionReason] = []

    # Full trace of all checks
    trace: list[DecisionTrace] = []

    # Context
    app_id: Optional[str] = None
    feature: Optional[str] = None
    environment: Optional[str] = None
    model: Optional[str] = None

    # Timing
    total_duration_ms: Optional[float] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

    def to_response(self) -> dict:
        """Convert to API response format."""
        return {
            "decision_id": self.decision_id,
            "request_id": self.request_id,
            "decision": self.decision.value,
            "allowed": self.allowed,
            "reason": self.primary_reason.dict() if self.primary_reason else None,
            "warnings": [w.dict() for w in self.warnings],
        }

    def to_audit(self) -> dict:
        """Convert to audit log format (full detail)."""
        return self.dict()


class DecisionBuilder:
    """Builder for constructing Decision objects."""

    def __init__(self, request_id: str):
        self.request_id = request_id
        self.decision_id = str(uuid.uuid4())
        self.start_time = datetime.utcnow()
        self.traces: list[DecisionTrace] = []
        self.reasons: list[DecisionReason] = []
        self.warnings: list[DecisionReason] = []
        self.context: dict = {}
        self._final_decision: Optional[DecisionType] = None

    def set_context(
        self,
        app_id: Optional[str] = None,
        feature: Optional[str] = None,
        environment: Optional[str] = None,
        model: Optional[str] = None,
    ) -> "DecisionBuilder":
        """Set request context."""
        self.context = {
            "app_id": app_id,
            "feature": feature,
            "environment": environment,
            "model": model,
        }
        return self

    def add_trace(
        self,
        source: DecisionSource,
        checked: str,
        result: DecisionType,
        matched: bool = False,
        rule_id: Optional[str] = None,
        rule_name: Optional[str] = None,
        condition: Optional[str] = None,
        actual_value: Any = None,
        expected_value: Any = None,
        duration_ms: Optional[float] = None,
    ) -> "DecisionBuilder":
        """Add a trace entry."""
        self.traces.append(
            DecisionTrace(
                source=source,
                checked=checked,
                result=result,
                matched=matched,
                rule_id=rule_id,
                rule_name=rule_name,
                condition=condition,
                actual_value=actual_value,
                expected_value=expected_value,
                duration_ms=duration_ms,
            )
        )
        return self

    def add_reason(
        self,
        source: DecisionSource,
        code: str,
        message: str,
        details: dict = None,
        rule_id: Optional[str] = None,
        rule_name: Optional[str] = None,
    ) -> "DecisionBuilder":
        """Add a reason (blocking)."""
        self.reasons.append(
            DecisionReason(
                source=source,
                code=code,
                message=message,
                details=details or {},
                rule_id=rule_id,
                rule_name=rule_name,
            )
        )
        return self

    def add_warning(
        self,
        source: DecisionSource,
        code: str,
        message: str,
        details: dict = None,
        rule_id: Optional[str] = None,
        rule_name: Optional[str] = None,
    ) -> "DecisionBuilder":
        """Add a warning (non-blocking)."""
        self.warnings.append(
            DecisionReason(
                source=source,
                code=code,
                message=message,
                details=details or {},
                rule_id=rule_id,
                rule_name=rule_name,
            )
        )
        return self

    def deny(
        self,
        source: DecisionSource,
        code: str,
        message: str,
        **kwargs,
    ) -> "DecisionBuilder":
        """Set decision to DENY with reason."""
        self._final_decision = DecisionType.DENY
        self.add_reason(source, code, message, **kwargs)
        return self

    def block(
        self,
        source: DecisionSource,
        code: str,
        message: str,
        **kwargs,
    ) -> "DecisionBuilder":
        """Set decision to BLOCK (security) with reason."""
        self._final_decision = DecisionType.BLOCK
        self.add_reason(source, code, message, **kwargs)
        return self

    def warn(
        self,
        source: DecisionSource,
        code: str,
        message: str,
        **kwargs,
    ) -> "DecisionBuilder":
        """Add a warning (doesn't change decision)."""
        if self._final_decision is None:
            self._final_decision = DecisionType.WARN
        self.add_warning(source, code, message, **kwargs)
        return self

    def allow(self) -> "DecisionBuilder":
        """Set decision to ALLOW."""
        if self._final_decision is None:
            self._final_decision = DecisionType.ALLOW
        return self

    def build(self) -> Decision:
        """Build the final Decision object."""
        end_time = datetime.utcnow()
        duration_ms = (end_time - self.start_time).total_seconds() * 1000

        # Determine final decision
        final = self._final_decision or DecisionType.ALLOW
        allowed = final in (DecisionType.ALLOW, DecisionType.WARN)

        # Get primary reason
        primary_reason = self.reasons[0] if self.reasons else None

        return Decision(
            decision_id=self.decision_id,
            request_id=self.request_id,
            timestamp=self.start_time,
            decision=final,
            allowed=allowed,
            primary_reason=primary_reason,
            reasons=self.reasons,
            warnings=self.warnings,
            trace=self.traces,
            app_id=self.context.get("app_id"),
            feature=self.context.get("feature"),
            environment=self.context.get("environment"),
            model=self.context.get("model"),
            total_duration_ms=duration_ms,
        )


# Pre-defined decision codes for consistency
class DecisionCodes:
    """Standard decision codes."""

    # Authentication
    AUTH_MISSING_KEY = "auth.missing_key"
    AUTH_INVALID_KEY = "auth.invalid_key"
    AUTH_EXPIRED_KEY = "auth.expired_key"
    AUTH_INACTIVE_KEY = "auth.inactive_key"

    # Authorization
    AUTHZ_PERMISSION_DENIED = "authz.permission_denied"
    AUTHZ_APP_NOT_ALLOWED = "authz.app_not_allowed"

    # Contract
    CONTRACT_MISSING = "contract.missing"
    CONTRACT_INVALID = "contract.invalid"
    CONTRACT_INCOMPLETE = "contract.incomplete"

    # Policy
    POLICY_MODEL_NOT_ALLOWED = "policy.model_not_allowed"
    POLICY_MAX_TOKENS_EXCEEDED = "policy.max_tokens_exceeded"
    POLICY_OUTSIDE_ALLOWED_HOURS = "policy.outside_allowed_hours"
    POLICY_ENVIRONMENT_DENIED = "policy.environment_denied"
    POLICY_CUSTOM_RULE = "policy.custom_rule"

    # Budget
    BUDGET_HARD_LIMIT = "budget.hard_limit_exceeded"
    BUDGET_SOFT_LIMIT = "budget.soft_limit_warning"
    BUDGET_NO_BUDGET = "budget.no_budget_configured"

    # Security
    SECURITY_PROMPT_INJECTION = "security.prompt_injection"
    SECURITY_SENSITIVE_DATA = "security.sensitive_data"
    SECURITY_INVALID_STRUCTURE = "security.invalid_structure"
    SECURITY_BLOCKED = "security.blocked"
    SECURITY_CONTENT_BLOCKED = "security.content_blocked"
    SECURITY_CONTENT_WARNING = "security.content_warning"
    SECURITY_PII_DETECTED = "security.pii_detected"
    SECURITY_TOXICITY_DETECTED = "security.toxicity_detected"

    # Rate limit
    RATE_LIMIT_EXCEEDED = "rate_limit.exceeded"

    # Feature
    FEATURE_NOT_ALLOWED = "feature.not_allowed"
    FEATURE_UNKNOWN = "feature.unknown"
    FEATURE_MODEL_MISMATCH = "feature.model_not_allowed_for_feature"


# Example usage helper
def create_decision(request_id: str) -> DecisionBuilder:
    """Create a new decision builder."""
    return DecisionBuilder(request_id)
