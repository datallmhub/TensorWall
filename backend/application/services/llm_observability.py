"""
LLM Observability Service - Governance-focused analytics.

Provides business-level insights for LLM governance:
- Cost breakdown by app/feature/model
- Token efficiency metrics
- Blocking statistics with cost avoided
- Anomaly detection (spikes, loops, unusual patterns)
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from enum import Enum
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import UsageRecord, LLMRequestTrace, TraceDecision
from backend.db.session import get_db_context


class TimePeriod(str, Enum):
    """Time period for analytics."""

    HOUR = "1h"
    DAY = "1d"
    WEEK = "7d"
    MONTH = "30d"
    QUARTER = "90d"


class CostBreakdownItem(BaseModel):
    """Single item in cost breakdown."""

    key: str  # app_id, feature_id, or model name
    name: str
    requests: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    percentage: float


class CostBreakdown(BaseModel):
    """Cost breakdown by different dimensions."""

    by_app: List[CostBreakdownItem]
    by_feature: List[CostBreakdownItem]
    by_model: List[CostBreakdownItem]
    by_environment: List[CostBreakdownItem]


class TokenEfficiency(BaseModel):
    """Token usage efficiency metrics."""

    input_output_ratio: float  # output / input
    avg_tokens_per_request: float
    avg_input_tokens: float
    avg_output_tokens: float
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int


class BlockingStats(BaseModel):
    """Statistics about blocked requests."""

    total_blocks: int
    rate_limit_blocks: int
    budget_blocks: int
    policy_blocks: int
    security_blocks: int
    feature_blocks: int
    cost_avoided_usd: float
    top_blocked_apps: List[Dict[str, Any]]


class AnomalyType(str, Enum):
    """Type of detected anomaly."""

    COST_SPIKE = "cost_spike"
    RETRY_LOOP = "retry_loop"
    UNUSUAL_PATTERN = "unusual_pattern"
    HIGH_ERROR_RATE = "high_error_rate"


class Anomaly(BaseModel):
    """Detected anomaly in LLM usage."""

    type: AnomalyType
    severity: str  # "low", "medium", "high", "critical"
    description: str
    app_id: Optional[str] = None
    feature_id: Optional[str] = None
    metric_value: float
    baseline_value: float
    deviation_percent: float
    detected_at: datetime
    details: Optional[Dict] = None


class GovernanceKPIs(BaseModel):
    """High-level governance KPIs."""

    period: str
    cost_breakdown: CostBreakdown
    token_efficiency: TokenEfficiency
    blocking_stats: BlockingStats
    anomalies: List[Anomaly]

    # Summary metrics
    total_cost_usd: float
    total_requests: int
    total_tokens: int
    cost_per_request: float
    cost_per_1k_tokens: float


class LLMObservabilityService:
    """
    Service for LLM governance observability.

    Focuses on business metrics, not infrastructure metrics.
    """

    async def get_governance_kpis(
        self,
        org_id: Optional[str] = None,
        app_id: Optional[str] = None,
        user_email: Optional[str] = None,
        feature: Optional[str] = None,
        environment: Optional[str] = None,
        period: TimePeriod = TimePeriod.DAY,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> GovernanceKPIs:
        """
        Get comprehensive governance KPIs with granular filtering.

        Args:
            org_id: Organization ID (optional filter)
            app_id: Application ID (optional filter)
            user_email: User email (optional filter)
            feature: Feature name (optional filter)
            environment: Environment (optional filter)
            period: Time period for analysis
            start_time: Optional custom start time
            end_time: Optional custom end time

        Returns:
            GovernanceKPIs with all governance metrics
        """
        # Calculate time range
        if not end_time:
            end_time = datetime.now(timezone.utc)
        if not start_time:
            start_time = self._calculate_start_time(end_time, period)

        async with get_db_context() as db:
            # Get request traces for period with filters
            traces = await self._get_request_traces(
                db, org_id, app_id, user_email, feature, environment, start_time, end_time
            )

            # Calculate metrics from traces
            cost_breakdown = await self._calculate_cost_breakdown_from_traces(db, traces)
            token_efficiency = self._calculate_token_efficiency_from_traces(traces)
            blocking_stats = self._calculate_blocking_stats_from_traces(traces)
            anomalies = await self._detect_anomalies_from_traces(db, traces, start_time, end_time)

            # Summary metrics from traces
            total_cost = sum(t.cost_usd for t in traces)
            total_requests = len(traces)
            total_tokens = sum(t.input_tokens + t.output_tokens for t in traces)

            return GovernanceKPIs(
                period=period.value,
                cost_breakdown=cost_breakdown,
                token_efficiency=token_efficiency,
                blocking_stats=blocking_stats,
                anomalies=anomalies,
                total_cost_usd=round(total_cost, 4),
                total_requests=total_requests,
                total_tokens=total_tokens,
                cost_per_request=round(total_cost / total_requests, 4) if total_requests > 0 else 0,
                cost_per_1k_tokens=round((total_cost / total_tokens) * 1000, 4)
                if total_tokens > 0
                else 0,
            )

    async def _get_request_traces(
        self,
        db: AsyncSession,
        org_id: Optional[str],
        app_id: Optional[str],
        user_email: Optional[str],
        feature: Optional[str],
        environment: Optional[str],
        start_time: datetime,
        end_time: datetime,
    ) -> List[LLMRequestTrace]:
        """
        Fetch request traces for the period with granular filters.

        This is the key query that enables drill-down from dashboard to individual requests.
        """
        # Convert timezone-aware to naive UTC for database compatibility
        start_naive = start_time.replace(tzinfo=None) if start_time.tzinfo else start_time
        end_naive = end_time.replace(tzinfo=None) if end_time.tzinfo else end_time

        stmt = select(LLMRequestTrace).where(
            LLMRequestTrace.timestamp_start >= start_naive,
            LLMRequestTrace.timestamp_start <= end_naive,
        )

        # Apply granular filters
        if org_id:
            stmt = stmt.where(LLMRequestTrace.tenant_id == org_id)
        if app_id:
            stmt = stmt.where(LLMRequestTrace.app_id == app_id)
        if user_email:
            stmt = stmt.where(LLMRequestTrace.user_email == user_email)
        if feature:
            stmt = stmt.where(LLMRequestTrace.feature == feature)
        if environment:
            from backend.db.models import Environment as EnvEnum

            stmt = stmt.where(LLMRequestTrace.environment == EnvEnum(environment))

        stmt = stmt.order_by(LLMRequestTrace.timestamp_start.desc())

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def _calculate_cost_breakdown_from_traces(
        self, db: AsyncSession, traces: List[LLMRequestTrace]
    ) -> CostBreakdown:
        """Calculate cost breakdown from traces (same logic, different source)."""
        # Traces have same attributes as UsageRecord, so we can reuse the logic
        return await self._calculate_cost_breakdown(db, traces)

    def _calculate_token_efficiency_from_traces(
        self, traces: List[LLMRequestTrace]
    ) -> TokenEfficiency:
        """Calculate token efficiency from traces."""
        return self._calculate_token_efficiency(traces)

    def _calculate_blocking_stats_from_traces(self, traces: List[LLMRequestTrace]) -> BlockingStats:
        """
        Calculate blocking statistics from traces.

        Now we can actually count blocks from the traces!
        """
        total_blocks = sum(1 for t in traces if t.decision == TraceDecision.BLOCK)

        # Count by reason categories
        rate_limit_blocks = sum(1 for t in traces if "rate_limit" in (t.decision_reasons or []))
        budget_blocks = sum(1 for t in traces if "budget" in (t.decision_reasons or []))
        policy_blocks = sum(1 for t in traces if "policy" in (t.decision_reasons or []))
        security_blocks = sum(
            1
            for t in traces
            if any(cat in ["prompt_injection", "pii_leakage"] for cat in (t.risk_categories or []))
        )

        # Calculate cost avoided
        cost_avoided = sum(
            t.estimated_cost_avoided for t in traces if t.decision == TraceDecision.BLOCK
        )

        # Top blocked apps
        blocked_by_app = {}
        for t in traces:
            if t.decision == TraceDecision.BLOCK:
                app_id = t.app_id or "unknown"
                blocked_by_app[app_id] = blocked_by_app.get(app_id, 0) + 1

        top_blocked = [
            {"app_id": app_id, "count": count}
            for app_id, count in sorted(blocked_by_app.items(), key=lambda x: x[1], reverse=True)[
                :10
            ]
        ]

        return BlockingStats(
            total_blocks=total_blocks,
            rate_limit_blocks=rate_limit_blocks,
            budget_blocks=budget_blocks,
            policy_blocks=policy_blocks,
            security_blocks=security_blocks,
            feature_blocks=0,  # Could add feature-based blocking
            cost_avoided_usd=cost_avoided,
            top_blocked_apps=top_blocked,
        )

    async def _detect_anomalies_from_traces(
        self,
        db: AsyncSession,
        traces: List[LLMRequestTrace],
        start_time: datetime,
        end_time: datetime,
    ) -> List[Anomaly]:
        """Detect anomalies from traces."""
        # Same logic as before, traces have same fields
        return await self._detect_anomalies(db, None, traces, start_time, end_time)

    async def _calculate_cost_breakdown(
        self, db: AsyncSession, usage_records: List[UsageRecord]
    ) -> CostBreakdown:
        """Calculate cost breakdown by different dimensions."""
        total_cost = sum(r.cost_usd for r in usage_records if r.cost_usd)

        # By app
        by_app = {}
        for record in usage_records:
            app_id = record.app_id or "unknown"
            if app_id not in by_app:
                by_app[app_id] = {
                    "requests": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0,
                }
            by_app[app_id]["requests"] += 1
            by_app[app_id]["input_tokens"] += record.input_tokens or 0
            by_app[app_id]["output_tokens"] += record.output_tokens or 0
            by_app[app_id]["cost_usd"] += record.cost_usd or 0.0

        by_app_items = [
            CostBreakdownItem(
                key=app_id,
                name=app_id,
                requests=stats["requests"],
                input_tokens=stats["input_tokens"],
                output_tokens=stats["output_tokens"],
                total_tokens=stats["input_tokens"] + stats["output_tokens"],
                cost_usd=round(stats["cost_usd"], 4),
                percentage=round((stats["cost_usd"] / total_cost) * 100, 2)
                if total_cost > 0
                else 0,
            )
            for app_id, stats in sorted(
                by_app.items(), key=lambda x: x[1]["cost_usd"], reverse=True
            )
        ]

        # By feature
        by_feature = {}
        for record in usage_records:
            feature = record.feature or "unknown"
            if feature not in by_feature:
                by_feature[feature] = {
                    "requests": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0,
                }
            by_feature[feature]["requests"] += 1
            by_feature[feature]["input_tokens"] += record.input_tokens or 0
            by_feature[feature]["output_tokens"] += record.output_tokens or 0
            by_feature[feature]["cost_usd"] += record.cost_usd or 0.0

        by_feature_items = [
            CostBreakdownItem(
                key=feature,
                name=feature,
                requests=stats["requests"],
                input_tokens=stats["input_tokens"],
                output_tokens=stats["output_tokens"],
                total_tokens=stats["input_tokens"] + stats["output_tokens"],
                cost_usd=round(stats["cost_usd"], 4),
                percentage=round((stats["cost_usd"] / total_cost) * 100, 2)
                if total_cost > 0
                else 0,
            )
            for feature, stats in sorted(
                by_feature.items(), key=lambda x: x[1]["cost_usd"], reverse=True
            )
        ]

        # By model
        by_model = {}
        for record in usage_records:
            model = record.model or "unknown"
            if model not in by_model:
                by_model[model] = {
                    "requests": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0,
                }
            by_model[model]["requests"] += 1
            by_model[model]["input_tokens"] += record.input_tokens or 0
            by_model[model]["output_tokens"] += record.output_tokens or 0
            by_model[model]["cost_usd"] += record.cost_usd or 0.0

        by_model_items = [
            CostBreakdownItem(
                key=model,
                name=model,
                requests=stats["requests"],
                input_tokens=stats["input_tokens"],
                output_tokens=stats["output_tokens"],
                total_tokens=stats["input_tokens"] + stats["output_tokens"],
                cost_usd=round(stats["cost_usd"], 4),
                percentage=round((stats["cost_usd"] / total_cost) * 100, 2)
                if total_cost > 0
                else 0,
            )
            for model, stats in sorted(
                by_model.items(), key=lambda x: x[1]["cost_usd"], reverse=True
            )
        ]

        # By environment
        by_env = {}
        for record in usage_records:
            env = record.environment or "unknown"
            if env not in by_env:
                by_env[env] = {
                    "requests": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0,
                }
            by_env[env]["requests"] += 1
            by_env[env]["input_tokens"] += record.input_tokens or 0
            by_env[env]["output_tokens"] += record.output_tokens or 0
            by_env[env]["cost_usd"] += record.cost_usd or 0.0

        by_env_items = [
            CostBreakdownItem(
                key=env,
                name=env,
                requests=stats["requests"],
                input_tokens=stats["input_tokens"],
                output_tokens=stats["output_tokens"],
                total_tokens=stats["input_tokens"] + stats["output_tokens"],
                cost_usd=round(stats["cost_usd"], 4),
                percentage=round((stats["cost_usd"] / total_cost) * 100, 2)
                if total_cost > 0
                else 0,
            )
            for env, stats in sorted(by_env.items(), key=lambda x: x[1]["cost_usd"], reverse=True)
        ]

        return CostBreakdown(
            by_app=by_app_items,
            by_feature=by_feature_items,
            by_model=by_model_items,
            by_environment=by_env_items,
        )

    def _calculate_token_efficiency(self, usage_records: List[UsageRecord]) -> TokenEfficiency:
        """Calculate token usage efficiency metrics."""
        if not usage_records:
            return TokenEfficiency(
                input_output_ratio=0,
                avg_tokens_per_request=0,
                avg_input_tokens=0,
                avg_output_tokens=0,
                total_requests=0,
                total_input_tokens=0,
                total_output_tokens=0,
            )

        total_input = sum(r.input_tokens or 0 for r in usage_records)
        total_output = sum(r.output_tokens or 0 for r in usage_records)
        total_requests = len(usage_records)

        return TokenEfficiency(
            input_output_ratio=round(total_output / total_input, 2) if total_input > 0 else 0,
            avg_tokens_per_request=round((total_input + total_output) / total_requests, 1),
            avg_input_tokens=round(total_input / total_requests, 1),
            avg_output_tokens=round(total_output / total_requests, 1),
            total_requests=total_requests,
            total_input_tokens=total_input,
            total_output_tokens=total_output,
        )

    async def _calculate_blocking_stats(
        self, db: AsyncSession, org_id: str, start_time: datetime, end_time: datetime
    ) -> BlockingStats:
        """
        Calculate statistics about blocked requests.

        Note: This is a placeholder. In production, you'd query audit_logs
        for DENY decisions and categorize them.
        """
        # Placeholder implementation
        # In production, query audit_logs for denied requests
        return BlockingStats(
            total_blocks=0,
            rate_limit_blocks=0,
            budget_blocks=0,
            policy_blocks=0,
            security_blocks=0,
            feature_blocks=0,
            cost_avoided_usd=0.0,
            top_blocked_apps=[],
        )

    async def _detect_anomalies(
        self,
        db: AsyncSession,
        org_id: str,
        usage_records: List[UsageRecord],
        start_time: datetime,
        end_time: datetime,
    ) -> List[Anomaly]:
        """
        Detect anomalies in LLM usage.

        Detects:
        - Cost spikes (>200% of baseline)
        - Retry loops (same feature, high frequency)
        - Unusual patterns
        """
        anomalies = []

        # Get baseline from previous period
        period_duration = end_time - start_time
        baseline_start = start_time - period_duration
        baseline_end = start_time

        baseline_records = await self._get_request_traces(
            db, org_id, None, None, None, None, baseline_start, baseline_end
        )

        # Detect cost spike
        current_cost = sum(r.cost_usd for r in usage_records)
        baseline_cost = sum(r.cost_usd for r in baseline_records)

        if baseline_cost > 0:
            cost_increase_percent = ((current_cost - baseline_cost) / baseline_cost) * 100

            if cost_increase_percent > 200:  # 200% increase
                anomalies.append(
                    Anomaly(
                        type=AnomalyType.COST_SPIKE,
                        severity="high" if cost_increase_percent > 500 else "medium",
                        description=f"Coût augmenté de {cost_increase_percent:.0f}% par rapport à la période précédente",
                        metric_value=current_cost,
                        baseline_value=baseline_cost,
                        deviation_percent=cost_increase_percent,
                        detected_at=datetime.now(timezone.utc),
                        details={
                            "current_period_cost": current_cost,
                            "baseline_period_cost": baseline_cost,
                        },
                    )
                )

        # Detect retry loops (same app+feature within short timeframe)
        if len(usage_records) > 10:
            app_feature_counts = {}
            for record in usage_records[-100:]:  # Last 100 requests
                key = f"{record.app_id}:{record.feature}"
                app_feature_counts[key] = app_feature_counts.get(key, 0) + 1

            for key, count in app_feature_counts.items():
                if count > 50:  # More than 50 identical requests
                    app_id, feature = key.split(":", 1)
                    anomalies.append(
                        Anomaly(
                            type=AnomalyType.RETRY_LOOP,
                            severity="high",
                            description=f"Boucle de retry détectée : {count} requêtes identiques",
                            app_id=app_id,
                            feature_id=feature,
                            metric_value=count,
                            baseline_value=10,
                            deviation_percent=((count - 10) / 10) * 100,
                            detected_at=datetime.now(timezone.utc),
                        )
                    )

        return anomalies

    def _calculate_start_time(self, end_time: datetime, period: TimePeriod) -> datetime:
        """Calculate start time based on period."""
        if period == TimePeriod.HOUR:
            return end_time - timedelta(hours=1)
        elif period == TimePeriod.DAY:
            return end_time - timedelta(days=1)
        elif period == TimePeriod.WEEK:
            return end_time - timedelta(days=7)
        elif period == TimePeriod.MONTH:
            return end_time - timedelta(days=30)
        elif period == TimePeriod.QUARTER:
            return end_time - timedelta(days=90)
        return end_time - timedelta(days=1)


# Singleton
llm_observability = LLMObservabilityService()
