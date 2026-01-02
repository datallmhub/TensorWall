"""
Decision Intelligence Service - Explainability for governance decisions.

Provides human-readable explanations for why requests were allowed/denied,
enabling compliance, audit, and troubleshooting.
"""

from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
from enum import Enum
from collections import Counter
from sqlalchemy import select

from backend.core.decisions import (
    Decision,
    DecisionStage,
    DecisionOutcome,
    DecisionCode,
)
from backend.db.models import LLMRequestTrace, TraceDecision
from backend.db.session import get_db_context


class DecisionSeverity(str, Enum):
    """Severity of a decision (for filtering/prioritization)."""

    CRITICAL = "critical"  # Hard blocks (security, compliance)
    HIGH = "high"  # Budget/quota exhausted
    MEDIUM = "medium"  # Rate limits, soft caps
    LOW = "low"  # Warnings, degraded service
    INFO = "info"  # Normal operation


class DecisionCategory(str, Enum):
    """High-level category for decisions."""

    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    BUDGET = "budget"
    RATE_LIMIT = "rate_limit"
    SECURITY = "security"
    POLICY = "policy"
    FEATURE = "feature"
    INPUT_VALIDATION = "input_validation"


class DecisionStep(BaseModel):
    """A single step in the decision chain."""

    stage: str
    outcome: str
    code: str
    reason: str
    details: Optional[dict] = None
    timestamp: Optional[datetime] = None


class DecisionExplanation(BaseModel):
    """Complete explanation of a governance decision."""

    request_id: str
    decision: str  # "ALLOW" or "DENY"
    decision_chain: List[DecisionStep]
    primary_reason: str
    category: DecisionCategory
    severity: DecisionSeverity

    # Human-readable explanation
    human_explanation: str
    technical_details: Optional[dict] = None

    # Remediation
    remediation: Optional[str] = None
    remediation_actions: Optional[List[str]] = None

    # Context
    app_id: Optional[str] = None
    feature_id: Optional[str] = None
    user_id: Optional[str] = None
    timestamp: datetime


class BlockingReasonSummary(BaseModel):
    """Summary of why requests are being blocked."""

    category: DecisionCategory
    code: str
    reason: str
    count: int
    percentage: float
    examples: List[str]  # Request IDs


class DecisionIntelligenceService:
    """
    Service for analyzing and explaining governance decisions.

    Provides:
    - Human-readable explanations for individual decisions
    - Aggregated blocking reasons
    - Decision analytics
    """

    def __init__(self):
        self._decision_cache = {}  # request_id -> Decision

    def explain_decision(
        self, request_id: str, decision: Decision, context: Optional[dict] = None
    ) -> DecisionExplanation:
        """
        Generate a complete explanation for a governance decision.

        Args:
            request_id: Unique request identifier
            decision: The Decision object from the decision engine
            context: Additional context (app_id, feature_id, etc.)

        Returns:
            DecisionExplanation with human-readable details
        """
        context = context or {}

        # Build decision chain
        decision_chain = []
        for stage_decision in decision.chain:
            decision_chain.append(
                DecisionStep(
                    stage=stage_decision.stage.value,
                    outcome=stage_decision.outcome.value,
                    code=stage_decision.code.value,
                    reason=stage_decision.reason,
                    details=stage_decision.details,
                    timestamp=datetime.now(timezone.utc),
                )
            )

        # Determine category and severity
        category, severity = self._categorize_decision(decision)

        # Generate human explanation
        human_explanation = self._generate_human_explanation(decision, context)

        # Generate remediation
        remediation = self._generate_remediation(decision, context)
        remediation_actions = self._generate_remediation_actions(decision, context)

        return DecisionExplanation(
            request_id=request_id,
            decision="DENY" if decision.decision == DecisionOutcome.DENY else "ALLOW",
            decision_chain=decision_chain,
            primary_reason=(
                decision.primary_reason.message
                if decision.primary_reason
                else "No reason provided"
            ),
            category=category,
            severity=severity,
            human_explanation=human_explanation,
            technical_details=self._extract_technical_details(decision),
            remediation=remediation,
            remediation_actions=remediation_actions,
            app_id=context.get("app_id"),
            feature_id=context.get("feature_id"),
            user_id=context.get("user_id"),
            timestamp=datetime.now(timezone.utc),
        )

    def _categorize_decision(
        self, decision: Decision
    ) -> tuple[DecisionCategory, DecisionSeverity]:
        """Categorize a decision by type and severity."""
        if not decision.primary_reason:
            return DecisionCategory.AUTHORIZATION, DecisionSeverity.INFO

        code = decision.primary_reason.code

        # Map decision codes to categories
        if code in [
            DecisionCode.AUTH_NO_KEY,
            DecisionCode.AUTH_INVALID_KEY,
            DecisionCode.AUTH_EXPIRED_KEY,
        ]:
            return DecisionCategory.AUTHENTICATION, DecisionSeverity.CRITICAL

        if code in [
            DecisionCode.AUTHZ_PERMISSION_DENIED,
            DecisionCode.AUTHZ_RESOURCE_FORBIDDEN,
        ]:
            return DecisionCategory.AUTHORIZATION, DecisionSeverity.HIGH

        if code in [
            DecisionCode.BUDGET_HARD_LIMIT_EXCEEDED,
            DecisionCode.BUDGET_MONTHLY_EXHAUSTED,
        ]:
            return DecisionCategory.BUDGET, DecisionSeverity.HIGH

        if code in [DecisionCode.BUDGET_SOFT_LIMIT_WARNING]:
            return DecisionCategory.BUDGET, DecisionSeverity.MEDIUM

        if code in [DecisionCode.RATE_LIMIT_EXCEEDED, DecisionCode.RATE_LIMIT_BURST]:
            return DecisionCategory.RATE_LIMIT, DecisionSeverity.MEDIUM

        if code in [
            DecisionCode.SECURITY_INJECTION_DETECTED,
            DecisionCode.SECURITY_PII_DETECTED,
        ]:
            return DecisionCategory.SECURITY, DecisionSeverity.CRITICAL

        if code in [DecisionCode.FEATURE_UNKNOWN, DecisionCode.FEATURE_DISABLED]:
            return DecisionCategory.FEATURE, DecisionSeverity.HIGH

        if code in [
            DecisionCode.INPUT_INVALID_SCHEMA,
            DecisionCode.INPUT_DATA_SEPARATION_VIOLATION,
        ]:
            return DecisionCategory.INPUT_VALIDATION, DecisionSeverity.HIGH

        return DecisionCategory.POLICY, DecisionSeverity.MEDIUM

    def _generate_human_explanation(self, decision: Decision, context: dict) -> str:
        """Generate a human-readable explanation in French."""
        if not decision.primary_reason:
            return "Requête autorisée sans restrictions."

        code = decision.primary_reason.code
        message = decision.primary_reason.message

        # Budget explanations
        if code == DecisionCode.BUDGET_HARD_LIMIT_EXCEEDED:
            return f"Cette requête a été refusée car le budget mensuel est épuisé. {message}"

        if code == DecisionCode.BUDGET_SOFT_LIMIT_WARNING:
            return f"Attention : le budget approche de sa limite. {message}"

        # Rate limit explanations
        if code == DecisionCode.RATE_LIMIT_EXCEEDED:
            return f"Cette requête a été refusée car la limite de débit a été atteinte. {message}"

        # Authentication explanations
        if code == DecisionCode.AUTH_INVALID_KEY:
            return f"Authentification refusée : clé API invalide. {message}"

        # Security explanations
        if code == DecisionCode.SECURITY_INJECTION_DETECTED:
            return f"Requête bloquée pour raisons de sécurité : tentative d'injection détectée. {message}"

        # Feature explanations
        if code == DecisionCode.FEATURE_UNKNOWN:
            return f"Cette fonctionnalité n'est pas enregistrée pour votre application. {message}"

        # Default
        return message

    def _generate_remediation(self, decision: Decision, context: dict) -> Optional[str]:
        """Generate remediation advice."""
        if not decision.primary_reason:
            return None

        code = decision.primary_reason.code

        if code == DecisionCode.BUDGET_HARD_LIMIT_EXCEEDED:
            return "Augmentez le budget mensuel ou attendez le prochain cycle de facturation."

        if code == DecisionCode.RATE_LIMIT_EXCEEDED:
            return "Réduisez la fréquence des requêtes ou demandez une augmentation de quota."

        if code == DecisionCode.AUTH_INVALID_KEY:
            return "Vérifiez que vous utilisez une clé API valide et active."

        if code == DecisionCode.FEATURE_UNKNOWN:
            return "Enregistrez cette fonctionnalité dans votre application ou utilisez une fonctionnalité existante."

        return "Contactez votre administrateur pour plus d'informations."

    def _generate_remediation_actions(
        self, decision: Decision, context: dict
    ) -> Optional[List[str]]:
        """Generate list of actionable remediation steps."""
        if not decision.primary_reason:
            return None

        code = decision.primary_reason.code

        if code == DecisionCode.BUDGET_HARD_LIMIT_EXCEEDED:
            return [
                "Accéder à /admin/budgets",
                "Augmenter la limite mensuelle",
                "Ou attendre le reset automatique le 1er du mois",
            ]

        if code == DecisionCode.RATE_LIMIT_EXCEEDED:
            return [
                "Implémenter un backoff exponentiel",
                "Réduire la fréquence des appels",
                "Demander une augmentation de quota via /admin/policies",
            ]

        if code == DecisionCode.FEATURE_UNKNOWN:
            return [
                "Accéder à /admin/features",
                "Enregistrer la fonctionnalité souhaitée",
                "Ou utiliser 'default' comme feature_id",
            ]

        return None

    def _extract_technical_details(self, decision: Decision) -> dict:
        """Extract technical details for debugging."""
        details = {
            "decision_id": decision.decision_id,
            "timestamp": decision.timestamp.isoformat() if decision.timestamp else None,
            "stages_evaluated": len(decision.chain),
        }

        if decision.primary_reason and decision.primary_reason.details:
            details["context"] = decision.primary_reason.details

        return details

    def get_blocking_reasons_summary(
        self, decisions: List[Decision], min_count: int = 1
    ) -> List[BlockingReasonSummary]:
        """
        Aggregate and summarize blocking reasons across multiple decisions.

        Args:
            decisions: List of Decision objects to analyze
            min_count: Minimum count to include in summary

        Returns:
            List of blocking reason summaries, sorted by frequency
        """
        # Count decisions by code
        code_counts = {}
        code_examples = {}

        for decision in decisions:
            if decision.decision != DecisionOutcome.DENY:
                continue

            if not decision.primary_reason:
                continue

            code = decision.primary_reason.code.value

            if code not in code_counts:
                code_counts[code] = 0
                code_examples[code] = []

            code_counts[code] += 1

            # Keep up to 5 examples
            if len(code_examples[code]) < 5:
                code_examples[code].append(decision.decision_id)

        # Build summaries
        total_blocked = sum(code_counts.values())
        summaries = []

        for code, count in code_counts.items():
            if count < min_count:
                continue

            # Recreate decision code enum
            decision_code = DecisionCode(code)

            # Categorize
            mock_decision = Decision(
                stage=DecisionStage.AUTHORIZATION,
                outcome=DecisionOutcome.DENY,
                code=decision_code,
                reason="Mock",
            )
            category, _ = self._categorize_decision(mock_decision)

            summaries.append(
                BlockingReasonSummary(
                    category=category,
                    code=code,
                    reason=self._get_code_description(decision_code),
                    count=count,
                    percentage=(
                        round((count / total_blocked) * 100, 2)
                        if total_blocked > 0
                        else 0
                    ),
                    examples=code_examples[code],
                )
            )

        # Sort by count descending
        summaries.sort(key=lambda x: x.count, reverse=True)

        return summaries

    def _get_code_description(self, code: DecisionCode) -> str:
        """Get human-readable description for a decision code."""
        descriptions = {
            DecisionCode.BUDGET_HARD_LIMIT_EXCEEDED: "Budget mensuel épuisé",
            DecisionCode.RATE_LIMIT_EXCEEDED: "Limite de débit dépassée",
            DecisionCode.AUTH_INVALID_KEY: "Clé API invalide",
            DecisionCode.FEATURE_UNKNOWN: "Fonctionnalité non enregistrée",
            DecisionCode.SECURITY_INJECTION_DETECTED: "Tentative d'injection détectée",
        }
        return descriptions.get(code, code.value)

    async def get_blocking_reasons(
        self, period: str = "24h", min_count: int = 1, limit: int = 10
    ) -> List[BlockingReasonSummary]:
        """
        Get top blocking reasons from actual traces in the database.

        Args:
            period: Time period (24h, 7d, 30d)
            min_count: Minimum count to include
            limit: Maximum number of reasons to return

        Returns:
            List of blocking reason summaries
        """
        # Parse period
        hours_map = {"1h": 1, "24h": 24, "7d": 168, "30d": 720}
        hours = hours_map.get(period, 24)
        # Use naive datetime since DB column is TIMESTAMP WITHOUT TIME ZONE
        start_time = datetime.now() - timedelta(hours=hours)

        # Query blocked traces
        blocked_traces = await self._fetch_blocked_traces(start_time)
        if not blocked_traces:
            return []

        # Aggregate reasons
        reason_data = self._aggregate_blocking_reasons(blocked_traces)

        # Build summaries
        return self._build_reason_summaries(reason_data, min_count, limit)

    async def _fetch_blocked_traces(
        self, start_time: datetime
    ) -> List[LLMRequestTrace]:
        """Fetch blocked traces from database."""
        async with get_db_context() as db:
            stmt = select(LLMRequestTrace).where(
                LLMRequestTrace.decision == TraceDecision.BLOCK,
                LLMRequestTrace.timestamp_start >= start_time,
            )
            result = await db.execute(stmt)
            return list(result.scalars().all())

    def _aggregate_blocking_reasons(
        self, blocked_traces: List[LLMRequestTrace]
    ) -> dict:
        """Aggregate blocking reasons from traces."""
        reason_counts = Counter()
        reason_examples = {}
        reason_categories = {}

        for trace in blocked_traces:
            reasons = trace.decision_reasons or ["Unknown reason"]
            primary_reason = reasons[0] if reasons else "Unknown reason"

            reason_counts[primary_reason] += 1

            if primary_reason not in reason_examples:
                reason_examples[primary_reason] = []
            if len(reason_examples[primary_reason]) < 3:
                reason_examples[primary_reason].append(trace.request_id)

            if primary_reason not in reason_categories:
                reason_categories[primary_reason] = self._categorize_reason(
                    primary_reason, trace.risk_categories or []
                )

        return {
            "counts": reason_counts,
            "examples": reason_examples,
            "categories": reason_categories,
        }

    def _build_reason_summaries(
        self, reason_data: dict, min_count: int, limit: int
    ) -> List[BlockingReasonSummary]:
        """Build blocking reason summaries from aggregated data."""
        reason_counts = reason_data["counts"]
        reason_examples = reason_data["examples"]
        reason_categories = reason_data["categories"]

        total_blocked = sum(reason_counts.values())
        summaries = []

        for reason, count in reason_counts.most_common(limit):
            if count < min_count:
                continue

            category = reason_categories.get(reason, DecisionCategory.POLICY)
            percentage = (
                round((count / total_blocked) * 100, 2) if total_blocked > 0 else 0
            )

            summaries.append(
                BlockingReasonSummary(
                    category=category,
                    code=self._reason_to_code(reason),
                    reason=reason,
                    count=count,
                    percentage=percentage,
                    examples=reason_examples.get(reason, []),
                )
            )

        return summaries

    def _categorize_reason(
        self, reason: str, risk_categories: List[str]
    ) -> DecisionCategory:
        """Categorize a blocking reason."""
        reason_lower = reason.lower()

        if (
            "budget" in reason_lower
            or "limit" in reason_lower
            or "cost" in reason_lower
        ):
            return DecisionCategory.BUDGET
        elif "rate" in reason_lower or "throttle" in reason_lower:
            return DecisionCategory.RATE_LIMIT
        elif (
            "security" in reason_lower
            or "injection" in reason_lower
            or "pii" in reason_lower
        ):
            return DecisionCategory.SECURITY
        elif (
            "feature" in reason_lower
            or "not registered" in reason_lower
            or "not allowed" in reason_lower
        ):
            return DecisionCategory.FEATURE
        elif "policy" in reason_lower or "rule" in reason_lower:
            return DecisionCategory.POLICY
        elif "auth" in reason_lower or "permission" in reason_lower:
            return DecisionCategory.AUTHORIZATION
        elif any(cat in ["prompt_injection", "pii_leakage"] for cat in risk_categories):
            return DecisionCategory.SECURITY
        else:
            return DecisionCategory.POLICY

    def _reason_to_code(self, reason: str) -> str:
        """Convert a reason string to a code."""
        reason_lower = reason.lower()

        if "budget" in reason_lower:
            return "BUDGET_EXCEEDED"
        elif "rate" in reason_lower:
            return "RATE_LIMIT"
        elif "feature" in reason_lower and "not registered" in reason_lower:
            return "FEATURE_NOT_REGISTERED"
        elif "security" in reason_lower:
            return "SECURITY_VIOLATION"
        elif "policy" in reason_lower:
            return "POLICY_VIOLATION"
        else:
            return "BLOCKED"


# Singleton
decision_intelligence = DecisionIntelligenceService()
