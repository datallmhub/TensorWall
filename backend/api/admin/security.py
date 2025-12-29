"""Security posture and governance endpoints.

Provides visibility into security rules, threats blocked, and OWASP alignment.
Security by default, visibility by design.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta

from backend.db.session import get_db
from backend.db.models import LLMRequestTrace, TraceDecision


router = APIRouter(prefix="/security")


# ============================================================================
# Schemas
# ============================================================================


class SecurityRule(BaseModel):
    """Security rule configuration."""

    name: str
    category: str
    action: str  # "block" | "warn"
    scope: str  # "global" | "environment" | "application"
    mandatory: bool
    enabled: bool
    description: str
    owasp_mapping: str | None = None


class ThreatMetrics(BaseModel):
    """Metrics for blocked threats."""

    total_blocked: int
    by_category: dict[str, int]
    trend_7d: list[dict]  # Daily counts for last 7 days


class OWASPAlignment(BaseModel):
    """OWASP Top 10 for LLM alignment status."""

    id: str
    name: str
    status: str  # "full" | "partial" | "na"
    coverage: str


class SecurityPosture(BaseModel):
    """Overall security posture."""

    status: str  # "protected" | "warning" | "critical"
    message: str
    active_rules: int
    total_rules: int
    owasp_coverage: list[OWASPAlignment]


class SecurityReport(BaseModel):
    """Complete security report."""

    posture: SecurityPosture
    threats: ThreatMetrics
    rules: list[SecurityRule]


# ============================================================================
# Default Security Rules (OWASP-aligned)
# ============================================================================

DEFAULT_SECURITY_RULES = [
    # LLM01 - Prompt Injection
    SecurityRule(
        name="Block Prompt Injection",
        category="Prompt Injection",
        action="block",
        scope="global",
        mandatory=True,
        enabled=True,
        description="Detects and blocks prompt injection attempts (system override, role confusion, instruction manipulation)",
        owasp_mapping="LLM01",
    ),
    SecurityRule(
        name="Detect Indirect Injection",
        category="Prompt Injection",
        action="warn",
        scope="global",
        mandatory=True,
        enabled=True,
        description="Detects indirect prompt injection from external sources",
        owasp_mapping="LLM01",
    ),
    # LLM02 - Insecure Output Handling
    SecurityRule(
        name="Enforce JSON Schema",
        category="Output Validation",
        action="block",
        scope="application",
        mandatory=False,
        enabled=True,
        description="Validates LLM outputs against defined JSON schemas",
        owasp_mapping="LLM02",
    ),
    SecurityRule(
        name="Validate Response Size",
        category="Output Validation",
        action="block",
        scope="global",
        mandatory=True,
        enabled=True,
        description="Blocks excessively large responses that could indicate abuse",
        owasp_mapping="LLM02",
    ),
    # LLM04 - Model Denial of Service
    SecurityRule(
        name="Rate Limiting",
        category="DoS Prevention",
        action="block",
        scope="global",
        mandatory=True,
        enabled=True,
        description="Prevents abuse through request rate limiting per user/app",
        owasp_mapping="LLM04",
    ),
    SecurityRule(
        name="Detect Retry Storms",
        category="DoS Prevention",
        action="block",
        scope="global",
        mandatory=True,
        enabled=True,
        description="Detects and blocks retry storms and infinite loops",
        owasp_mapping="LLM04",
    ),
    SecurityRule(
        name="Token Explosion Control",
        category="DoS Prevention",
        action="block",
        scope="environment",
        mandatory=True,
        enabled=True,
        description="Enforces maximum token limits per request to prevent resource exhaustion",
        owasp_mapping="LLM04",
    ),
    SecurityRule(
        name="Budget Hard Stop",
        category="DoS Prevention",
        action="block",
        scope="global",
        mandatory=True,
        enabled=True,
        description="Hard budget limits prevent cost-based DoS attacks",
        owasp_mapping="LLM04",
    ),
    # LLM05 - Supply Chain Vulnerabilities
    SecurityRule(
        name="Restrict Models by Environment",
        category="Model Governance",
        action="block",
        scope="environment",
        mandatory=True,
        enabled=True,
        description="Whitelists approved models per environment (dev/staging/prod)",
        owasp_mapping="LLM05",
    ),
    SecurityRule(
        name="Block Deprecated Models",
        category="Model Governance",
        action="block",
        scope="global",
        mandatory=True,
        enabled=True,
        description="Prevents use of deprecated or insecure model versions",
        owasp_mapping="LLM05",
    ),
    # LLM06 - Sensitive Information Disclosure
    SecurityRule(
        name="Block Secrets & API Keys",
        category="Data Exfiltration",
        action="block",
        scope="global",
        mandatory=True,
        enabled=True,
        description="Detects and blocks API keys, passwords, tokens, and private keys",
        owasp_mapping="LLM06",
    ),
    SecurityRule(
        name="Detect PII",
        category="Data Exfiltration",
        action="warn",
        scope="global",
        mandatory=True,
        enabled=True,
        description="Detects personally identifiable information (emails, SSN, phone numbers)",
        owasp_mapping="LLM06",
    ),
    SecurityRule(
        name="Warn on Data Exfiltration",
        category="Data Exfiltration",
        action="warn",
        scope="global",
        mandatory=True,
        enabled=True,
        description="Detects patterns indicating potential data exfiltration attempts",
        owasp_mapping="LLM06",
    ),
    # LLM08 - Excessive Agency
    SecurityRule(
        name="Feature Allowlisting",
        category="Excessive Agency",
        action="block",
        scope="application",
        mandatory=True,
        enabled=True,
        description="Restricts model capabilities to explicitly allowed features per application",
        owasp_mapping="LLM08",
    ),
    SecurityRule(
        name="Environment-based Restrictions",
        category="Excessive Agency",
        action="block",
        scope="environment",
        mandatory=True,
        enabled=True,
        description="Enforces stricter controls in production environments",
        owasp_mapping="LLM08",
    ),
    # LLM09 - Overreliance
    SecurityRule(
        name="Output Validation & Warnings",
        category="Overreliance Prevention",
        action="warn",
        scope="global",
        mandatory=True,
        enabled=True,
        description="Validates outputs and warns on potentially unsafe responses",
        owasp_mapping="LLM09",
    ),
    # LLM10 - Model Theft
    SecurityRule(
        name="Abuse Detection",
        category="Model Theft Prevention",
        action="block",
        scope="global",
        mandatory=True,
        enabled=True,
        description="Detects suspicious patterns that may indicate model extraction attempts",
        owasp_mapping="LLM10",
    ),
]


OWASP_ALIGNMENT = [
    OWASPAlignment(
        id="LLM01",
        name="Prompt Injection",
        status="full",
        coverage="Direct & indirect injection detection with blocking",
    ),
    OWASPAlignment(
        id="LLM02",
        name="Insecure Output Handling",
        status="full",
        coverage="JSON schema validation, size limits, content filtering",
    ),
    OWASPAlignment(
        id="LLM03",
        name="Training Data Poisoning",
        status="na",
        coverage="Out of scope for API gateway (provider responsibility)",
    ),
    OWASPAlignment(
        id="LLM04",
        name="Model Denial of Service",
        status="full",
        coverage="Rate limiting, retry storm detection, token limits, budget controls",
    ),
    OWASPAlignment(
        id="LLM05",
        name="Supply Chain Vulnerabilities",
        status="partial",
        coverage="Model whitelisting, deprecated model blocking",
    ),
    OWASPAlignment(
        id="LLM06",
        name="Sensitive Information Disclosure",
        status="full",
        coverage="Secrets detection, PII detection, exfiltration warnings",
    ),
    OWASPAlignment(
        id="LLM07",
        name="Insecure Plugin Design",
        status="na",
        coverage="Not applicable (no plugin execution)",
    ),
    OWASPAlignment(
        id="LLM08",
        name="Excessive Agency",
        status="full",
        coverage="Feature allowlisting, environment-based restrictions",
    ),
    OWASPAlignment(
        id="LLM09",
        name="Overreliance",
        status="partial",
        coverage="Output validation and explainability features",
    ),
    OWASPAlignment(
        id="LLM10",
        name="Model Theft",
        status="partial",
        coverage="Rate limiting and abuse detection patterns",
    ),
]


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/report", response_model=SecurityReport)
async def get_security_report(
    period: str = "7d",
    db: AsyncSession = Depends(get_db),
):
    """
    Get complete security report.

    Shows:
    - Overall security posture
    - Threats blocked
    - Active security rules
    - OWASP alignment
    """
    # Calculate time range
    days = int(period.replace("d", ""))
    start_date = datetime.utcnow() - timedelta(days=days)

    # Get blocked requests
    result = await db.execute(
        select(func.count(LLMRequestTrace.id))
        .where(LLMRequestTrace.decision == TraceDecision.BLOCK)
        .where(LLMRequestTrace.timestamp_start >= start_date)
    )
    total_blocked = result.scalar() or 0

    # Get all blocked requests to analyze decision_reasons
    blocked_traces = await db.execute(
        select(LLMRequestTrace)
        .where(LLMRequestTrace.decision == TraceDecision.BLOCK)
        .where(LLMRequestTrace.timestamp_start >= start_date)
    )

    by_category = {}
    for trace in blocked_traces.scalars():
        # Parse category from decision_reasons (JSON array)
        reasons = trace.decision_reasons if trace.decision_reasons else []
        for reason in reasons:
            reason_str = str(reason).lower()
            if "injection" in reason_str:
                category = "Prompt Injection"
            elif "secret" in reason_str or "key" in reason_str or "pii" in reason_str:
                category = "Data Exfiltration"
            elif "token" in reason_str or "budget" in reason_str:
                category = "DoS Prevention"
            elif "model" in reason_str:
                category = "Model Governance"
            else:
                category = "Other"

            by_category[category] = by_category.get(category, 0) + 1
            break  # Count each trace only once

    # Get daily trend for last 7 days
    trend_7d = []
    for i in range(7):
        day_start = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=6 - i)
        day_end = day_start + timedelta(days=1)

        result = await db.execute(
            select(func.count(LLMRequestTrace.id))
            .where(LLMRequestTrace.decision == TraceDecision.BLOCK)
            .where(LLMRequestTrace.timestamp_start >= day_start)
            .where(LLMRequestTrace.timestamp_start < day_end)
        )
        count = result.scalar() or 0

        trend_7d.append(
            {
                "date": day_start.strftime("%Y-%m-%d"),
                "blocked": count,
            }
        )

    # Build security posture
    active_rules = len([r for r in DEFAULT_SECURITY_RULES if r.enabled])
    total_rules = len(DEFAULT_SECURITY_RULES)

    posture = SecurityPosture(
        status="protected",
        message="All critical protections are enabled",
        active_rules=active_rules,
        total_rules=total_rules,
        owasp_coverage=OWASP_ALIGNMENT,
    )

    threats = ThreatMetrics(
        total_blocked=total_blocked,
        by_category=by_category,
        trend_7d=trend_7d,
    )

    return SecurityReport(
        posture=posture,
        threats=threats,
        rules=DEFAULT_SECURITY_RULES,
    )


@router.get("/posture", response_model=SecurityPosture)
async def get_security_posture():
    """Get security posture summary."""
    active_rules = len([r for r in DEFAULT_SECURITY_RULES if r.enabled])
    total_rules = len(DEFAULT_SECURITY_RULES)

    return SecurityPosture(
        status="protected",
        message="All critical protections are enabled",
        active_rules=active_rules,
        total_rules=total_rules,
        owasp_coverage=OWASP_ALIGNMENT,
    )


@router.get("/rules", response_model=list[SecurityRule])
async def get_security_rules():
    """Get all security rules (read-only in V1)."""
    return DEFAULT_SECURITY_RULES


@router.get("/threats", response_model=ThreatMetrics)
async def get_threat_metrics(
    period: str = "7d",
    db: AsyncSession = Depends(get_db),
):
    """Get threat blocking metrics."""
    days = int(period.replace("d", ""))
    start_date = datetime.utcnow() - timedelta(days=days)

    # Total blocked
    result = await db.execute(
        select(func.count(LLMRequestTrace.id))
        .where(LLMRequestTrace.decision == TraceDecision.BLOCK)
        .where(LLMRequestTrace.timestamp_start >= start_date)
    )
    total_blocked = result.scalar() or 0

    # By category
    blocked_traces = await db.execute(
        select(LLMRequestTrace)
        .where(LLMRequestTrace.decision == TraceDecision.BLOCK)
        .where(LLMRequestTrace.timestamp_start >= start_date)
    )

    by_category = {}
    for trace in blocked_traces.scalars():
        reasons = trace.decision_reasons if trace.decision_reasons else []
        for reason in reasons:
            reason_str = str(reason).lower()
            if "injection" in reason_str:
                category = "Prompt Injection"
            elif "secret" in reason_str or "key" in reason_str or "pii" in reason_str:
                category = "Data Exfiltration"
            elif "token" in reason_str or "budget" in reason_str:
                category = "DoS Prevention"
            elif "model" in reason_str:
                category = "Model Governance"
            else:
                category = "Other"

            by_category[category] = by_category.get(category, 0) + 1
            break

    # Trend
    trend_7d = []
    for i in range(7):
        day_start = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=6 - i)
        day_end = day_start + timedelta(days=1)

        result = await db.execute(
            select(func.count(LLMRequestTrace.id))
            .where(LLMRequestTrace.decision == TraceDecision.BLOCK)
            .where(LLMRequestTrace.timestamp_start >= day_start)
            .where(LLMRequestTrace.timestamp_start < day_end)
        )
        count = result.scalar() or 0

        trend_7d.append(
            {
                "date": day_start.strftime("%Y-%m-%d"),
                "blocked": count,
            }
        )

    return ThreatMetrics(
        total_blocked=total_blocked,
        by_category=by_category,
        trend_7d=trend_7d,
    )
