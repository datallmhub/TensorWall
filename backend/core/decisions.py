"""
Decision Explainability - First-class decision tracking.

Ce module fournit une structure standard pour toutes les décisions
du pipeline, exploitable par humains et machines.
"""

from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class DecisionStage(str, Enum):
    """Étapes du pipeline où une décision peut être prise."""

    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    FEATURE_CHECK = "feature_check"
    POLICY_CHECK = "policy_check"
    BUDGET_CHECK = "budget_check"
    SECURITY_CHECK = "security_check"
    ABUSE_CHECK = "abuse_check"
    INPUT_VALIDATION = "input_validation"
    RATE_LIMIT = "rate_limit"
    OUTPUT_VALIDATION = "output_validation"
    LLM_CALL = "llm_call"


class DecisionOutcome(str, Enum):
    """Résultat d'une décision."""

    ALLOW = "allow"
    DENY = "deny"
    WARN = "warn"
    THROTTLE = "throttle"
    MODIFY = "modify"  # Request/response modifié
    ERROR = "error"


class DecisionCode(str, Enum):
    """Codes de décision standardisés."""

    # Authentication
    AUTH_SUCCESS = "AUTH_SUCCESS"
    AUTH_MISSING_KEY = "AUTH_MISSING_KEY"
    AUTH_INVALID_KEY = "AUTH_INVALID_KEY"
    AUTH_KEY_DISABLED = "AUTH_KEY_DISABLED"
    AUTH_KEY_EXPIRED = "AUTH_KEY_EXPIRED"

    # Authorization / RBAC
    AUTHZ_ALLOWED = "AUTHZ_ALLOWED"
    AUTHZ_INSUFFICIENT_ROLE = "AUTHZ_INSUFFICIENT_ROLE"
    AUTHZ_RESOURCE_FORBIDDEN = "AUTHZ_RESOURCE_FORBIDDEN"

    # Feature Enforcement
    FEATURE_ALLOWED = "FEATURE_ALLOWED"
    FEATURE_UNKNOWN = "FEATURE_UNKNOWN"
    FEATURE_DISABLED = "FEATURE_DISABLED"
    FEATURE_ACTION_FORBIDDEN = "FEATURE_ACTION_FORBIDDEN"
    FEATURE_MODEL_FORBIDDEN = "FEATURE_MODEL_FORBIDDEN"
    FEATURE_ENV_FORBIDDEN = "FEATURE_ENV_FORBIDDEN"
    FEATURE_TOKEN_EXCEEDED = "FEATURE_TOKEN_EXCEEDED"
    FEATURE_COST_EXCEEDED = "FEATURE_COST_EXCEEDED"

    # Policy
    POLICY_ALLOWED = "POLICY_ALLOWED"
    POLICY_MODEL_BLOCKED = "POLICY_MODEL_BLOCKED"
    POLICY_TOKEN_LIMIT = "POLICY_TOKEN_LIMIT"
    POLICY_ENV_RESTRICTION = "POLICY_ENV_RESTRICTION"
    POLICY_TIME_RESTRICTION = "POLICY_TIME_RESTRICTION"
    POLICY_RATE_LIMITED = "POLICY_RATE_LIMITED"

    # Budget
    BUDGET_OK = "BUDGET_OK"
    BUDGET_WARNING = "BUDGET_WARNING"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    BUDGET_FORECAST_EXCEEDED = "BUDGET_FORECAST_EXCEEDED"

    # Security
    SECURITY_CLEAN = "SECURITY_CLEAN"
    SECURITY_PII_DETECTED = "SECURITY_PII_DETECTED"
    SECURITY_INJECTION_DETECTED = "SECURITY_INJECTION_DETECTED"
    SECURITY_SECRET_DETECTED = "SECURITY_SECRET_DETECTED"
    SECURITY_SENSITIVE_TOPIC = "SECURITY_SENSITIVE_TOPIC"
    SECURITY_INSTRUCTION_LEAK = "SECURITY_INSTRUCTION_LEAK"

    # Input Validation
    INPUT_VALID = "INPUT_VALID"
    INPUT_INVALID_SCHEMA = "INPUT_INVALID_SCHEMA"
    INPUT_DATA_SEPARATION_VIOLATION = "INPUT_DATA_SEPARATION_VIOLATION"
    INPUT_MALFORMED = "INPUT_MALFORMED"

    # Abuse
    ABUSE_NONE = "ABUSE_NONE"
    ABUSE_LOOP_DETECTED = "ABUSE_LOOP_DETECTED"
    ABUSE_RATE_SPIKE = "ABUSE_RATE_SPIKE"
    ABUSE_COST_SPIKE = "ABUSE_COST_SPIKE"

    # Output
    OUTPUT_VALID = "OUTPUT_VALID"
    OUTPUT_FILTERED = "OUTPUT_FILTERED"
    OUTPUT_TRUNCATED = "OUTPUT_TRUNCATED"
    OUTPUT_FORMAT_INVALID = "OUTPUT_FORMAT_INVALID"

    # LLM
    LLM_SUCCESS = "LLM_SUCCESS"
    LLM_ERROR = "LLM_ERROR"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_RATE_LIMITED = "LLM_RATE_LIMITED"

    # Generic
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class Decision(BaseModel):
    """
    Structure standard d'une décision du pipeline.

    Designed for:
    - Human readability
    - Machine processing
    - Audit compliance
    - Debugging
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # Core decision
    outcome: DecisionOutcome
    stage: DecisionStage
    code: DecisionCode

    # Human-readable explanation
    reason: str
    explanation: Optional[str] = None  # More detailed explanation

    # Context
    request_id: Optional[str] = None
    app_id: Optional[str] = None
    feature_id: Optional[str] = None
    environment: Optional[str] = None

    # Related entities
    policy_id: Optional[str] = None
    budget_id: Optional[str] = None
    rule_id: Optional[str] = None

    # Technical details
    details: dict[str, Any] = {}

    # Timing
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    duration_ms: Optional[float] = None

    # Tracing
    trace_id: Optional[str] = None
    span_id: Optional[str] = None

    def to_audit_dict(self) -> dict:
        """Format pour audit log."""
        return {
            "decision_id": self.id,
            "outcome": self.outcome.value,
            "stage": self.stage.value,
            "code": self.code.value,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
            "app_id": self.app_id,
            "feature_id": self.feature_id,
            "policy_id": self.policy_id,
        }

    def to_response_dict(self) -> dict:
        """Format pour réponse API (safe pour client)."""
        return {
            "decision": self.outcome.value,
            "stage": self.stage.value,
            "code": self.code.value,
            "reason": self.reason,
        }


class DecisionChain(BaseModel):
    """
    Chaîne de décisions pour une requête.

    Permet de tracer toutes les décisions prises
    pendant le traitement d'une requête.
    """

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    decisions: list[Decision] = []

    # Final outcome
    final_outcome: Optional[DecisionOutcome] = None
    blocking_decision: Optional[Decision] = None

    # Timing
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Context
    app_id: Optional[str] = None
    feature_id: Optional[str] = None
    model: Optional[str] = None
    environment: Optional[str] = None

    def add_decision(self, decision: Decision) -> None:
        """Ajoute une décision à la chaîne."""
        decision.request_id = self.request_id
        if self.app_id:
            decision.app_id = self.app_id
        if self.feature_id:
            decision.feature_id = self.feature_id
        if self.environment:
            decision.environment = self.environment

        self.decisions.append(decision)

        # Update final outcome if blocking
        if decision.outcome == DecisionOutcome.DENY:
            self.final_outcome = DecisionOutcome.DENY
            self.blocking_decision = decision
        elif decision.outcome == DecisionOutcome.ERROR and not self.blocking_decision:
            self.final_outcome = DecisionOutcome.ERROR
            self.blocking_decision = decision

    def complete(self, outcome: Optional[DecisionOutcome] = None) -> None:
        """Marque la chaîne comme complète."""
        self.completed_at = datetime.utcnow()
        if outcome:
            self.final_outcome = outcome
        elif not self.final_outcome:
            self.final_outcome = DecisionOutcome.ALLOW

    def is_allowed(self) -> bool:
        """Vérifie si la requête est autorisée."""
        return self.final_outcome in (DecisionOutcome.ALLOW, DecisionOutcome.WARN, None)

    def get_blocking_reason(self) -> Optional[str]:
        """Retourne la raison du blocage si applicable."""
        if self.blocking_decision:
            return self.blocking_decision.reason
        return None

    def get_warnings(self) -> list[Decision]:
        """Retourne toutes les décisions de type WARN."""
        return [d for d in self.decisions if d.outcome == DecisionOutcome.WARN]

    def to_summary(self) -> dict:
        """Résumé de la chaîne de décisions."""
        return {
            "request_id": self.request_id,
            "final_outcome": self.final_outcome.value if self.final_outcome else None,
            "total_decisions": len(self.decisions),
            "blocking_decision": (
                self.blocking_decision.to_response_dict()
                if self.blocking_decision
                else None
            ),
            "warnings": [d.to_response_dict() for d in self.get_warnings()],
            "duration_ms": (
                (self.completed_at - self.started_at).total_seconds() * 1000
                if self.completed_at
                else None
            ),
        }

    def to_full_trace(self) -> dict:
        """Trace complète pour debugging."""
        return {
            "request_id": self.request_id,
            "app_id": self.app_id,
            "feature_id": self.feature_id,
            "model": self.model,
            "environment": self.environment,
            "final_outcome": self.final_outcome.value if self.final_outcome else None,
            "started_at": self.started_at.isoformat(),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "decisions": [
                {
                    "stage": d.stage.value,
                    "outcome": d.outcome.value,
                    "code": d.code.value,
                    "reason": d.reason,
                    "policy_id": d.policy_id,
                    "details": d.details,
                    "timestamp": d.timestamp.isoformat(),
                }
                for d in self.decisions
            ],
        }


class DecisionBuilder:
    """Builder pour créer des décisions de manière fluide."""

    def __init__(self):
        self._stage: Optional[DecisionStage] = None
        self._outcome: Optional[DecisionOutcome] = None
        self._code: Optional[DecisionCode] = None
        self._reason: str = ""
        self._explanation: Optional[str] = None
        self._details: dict = {}
        self._policy_id: Optional[str] = None
        self._budget_id: Optional[str] = None

    def stage(self, stage: DecisionStage) -> "DecisionBuilder":
        self._stage = stage
        return self

    def allow(self, code: DecisionCode, reason: str) -> "DecisionBuilder":
        self._outcome = DecisionOutcome.ALLOW
        self._code = code
        self._reason = reason
        return self

    def deny(self, code: DecisionCode, reason: str) -> "DecisionBuilder":
        self._outcome = DecisionOutcome.DENY
        self._code = code
        self._reason = reason
        return self

    def warn(self, code: DecisionCode, reason: str) -> "DecisionBuilder":
        self._outcome = DecisionOutcome.WARN
        self._code = code
        self._reason = reason
        return self

    def error(self, code: DecisionCode, reason: str) -> "DecisionBuilder":
        self._outcome = DecisionOutcome.ERROR
        self._code = code
        self._reason = reason
        return self

    def with_explanation(self, explanation: str) -> "DecisionBuilder":
        self._explanation = explanation
        return self

    def with_details(self, **kwargs) -> "DecisionBuilder":
        self._details.update(kwargs)
        return self

    def with_policy(self, policy_id: str) -> "DecisionBuilder":
        self._policy_id = policy_id
        return self

    def with_budget(self, budget_id: str) -> "DecisionBuilder":
        self._budget_id = budget_id
        return self

    def build(self) -> Decision:
        if not self._stage or not self._outcome or not self._code:
            raise ValueError("Decision requires stage, outcome, and code")

        return Decision(
            stage=self._stage,
            outcome=self._outcome,
            code=self._code,
            reason=self._reason,
            explanation=self._explanation,
            details=self._details,
            policy_id=self._policy_id,
            budget_id=self._budget_id,
        )


# Convenience functions
def allow_decision(
    stage: DecisionStage, code: DecisionCode, reason: str, **details
) -> Decision:
    """Crée une décision ALLOW."""
    return Decision(
        stage=stage,
        outcome=DecisionOutcome.ALLOW,
        code=code,
        reason=reason,
        details=details,
    )


def deny_decision(
    stage: DecisionStage,
    code: DecisionCode,
    reason: str,
    policy_id: Optional[str] = None,
    **details,
) -> Decision:
    """Crée une décision DENY."""
    return Decision(
        stage=stage,
        outcome=DecisionOutcome.DENY,
        code=code,
        reason=reason,
        policy_id=policy_id,
        details=details,
    )


def warn_decision(
    stage: DecisionStage, code: DecisionCode, reason: str, **details
) -> Decision:
    """Crée une décision WARN."""
    return Decision(
        stage=stage,
        outcome=DecisionOutcome.WARN,
        code=code,
        reason=reason,
        details=details,
    )
