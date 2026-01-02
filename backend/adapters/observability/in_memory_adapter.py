"""In-Memory Observability Adapter.

Architecture Hexagonale: Implementation native du ObservabilityPort
pour l'observabilite enrichie sans dependance externe.
"""

import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass

from backend.ports.observability import (
    ObservabilityPort,
    CostFilters,
    CostBreakdown,
    TokenEfficiency,
    Anomaly,
    AnomalyType,
    AnomalySeverity,
    GovernanceKPIs,
)


@dataclass
class UsageRecord:
    """Record of usage for analytics."""

    timestamp: datetime
    app_id: str
    org_id: str
    model: str
    environment: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: float
    allowed: bool
    error: bool = False


class InMemoryObservabilityAdapter(ObservabilityPort):
    """
    Native implementation of observability.

    Stores usage data in memory for analytics, cost tracking,
    anomaly detection, and governance KPIs.
    """

    def __init__(
        self,
        anomaly_threshold_percent: float = 50.0,
        cost_per_1k_input_tokens: float = 0.01,
        cost_per_1k_output_tokens: float = 0.03,
    ):
        self._records: list[UsageRecord] = []
        self._anomaly_threshold = anomaly_threshold_percent
        self._cost_per_1k_input = cost_per_1k_input_tokens
        self._cost_per_1k_output = cost_per_1k_output_tokens

    def record_usage(
        self,
        app_id: str,
        org_id: str,
        model: str,
        environment: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        allowed: bool,
        error: bool = False,
        timestamp: datetime | None = None,
    ) -> None:
        """Record a usage event."""
        cost = (input_tokens / 1000) * self._cost_per_1k_input + (
            output_tokens / 1000
        ) * self._cost_per_1k_output
        self._records.append(
            UsageRecord(
                timestamp=timestamp or datetime.now(),
                app_id=app_id,
                org_id=org_id,
                model=model,
                environment=environment,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
                latency_ms=latency_ms,
                allowed=allowed,
                error=error,
            )
        )

    async def record_request(
        self,
        app_id: str,
        org_id: str,
        model: str,
        environment: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        latency_ms: float,
        outcome: str,
        feature: str | None = None,
    ) -> None:
        """Record request metrics (async wrapper around record_usage)."""
        allowed = outcome == "allowed"
        error = outcome == "error"
        self.record_usage(
            app_id=app_id,
            org_id=org_id,
            model=model,
            environment=environment,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            allowed=allowed,
            error=error,
        )

    async def get_cost_breakdown(
        self,
        filters: CostFilters,
    ) -> CostBreakdown:
        """Get cost breakdown with filters."""
        filtered = self._apply_filters(filters)

        by_model: dict[str, float] = {}
        by_app: dict[str, float] = {}
        by_environment: dict[str, float] = {}
        by_day: dict[str, float] = {}
        total = 0.0

        for record in filtered:
            total += record.cost_usd
            by_model[record.model] = by_model.get(record.model, 0) + record.cost_usd
            by_app[record.app_id] = by_app.get(record.app_id, 0) + record.cost_usd
            by_environment[record.environment] = (
                by_environment.get(record.environment, 0) + record.cost_usd
            )
            day_key = record.timestamp.strftime("%Y-%m-%d")
            by_day[day_key] = by_day.get(day_key, 0) + record.cost_usd

        return CostBreakdown(
            total_cost_usd=round(total, 4),
            by_model={k: round(v, 4) for k, v in by_model.items()},
            by_app={k: round(v, 4) for k, v in by_app.items()},
            by_environment={k: round(v, 4) for k, v in by_environment.items()},
            by_day={k: round(v, 4) for k, v in by_day.items()},
            period_start=filters.start_date,
            period_end=filters.end_date,
        )

    async def get_token_efficiency(
        self,
        app_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> TokenEfficiency:
        """Get token efficiency for an app."""
        filtered = [
            r
            for r in self._records
            if r.app_id == app_id
            and (start_date is None or r.timestamp >= start_date)
            and (end_date is None or r.timestamp <= end_date)
        ]

        if not filtered:
            return TokenEfficiency(
                app_id=app_id,
                total_input_tokens=0,
                total_output_tokens=0,
                avg_input_per_request=0.0,
                avg_output_per_request=0.0,
                input_output_ratio=0.0,
                cost_per_1k_tokens=0.0,
            )

        total_input = sum(r.input_tokens for r in filtered)
        total_output = sum(r.output_tokens for r in filtered)
        total_cost = sum(r.cost_usd for r in filtered)
        count = len(filtered)
        total_tokens = total_input + total_output

        return TokenEfficiency(
            app_id=app_id,
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            avg_input_per_request=round(total_input / count, 2),
            avg_output_per_request=round(total_output / count, 2),
            input_output_ratio=round(total_input / max(total_output, 1), 2),
            cost_per_1k_tokens=round((total_cost / max(total_tokens, 1)) * 1000, 4),
        )

    async def detect_anomalies(
        self,
        app_id: str | None = None,
        lookback_hours: int = 24,
    ) -> list[Anomaly]:
        """Detect anomalies in usage patterns."""
        cutoff = datetime.now() - timedelta(hours=lookback_hours)
        recent = [
            r
            for r in self._records
            if r.timestamp >= cutoff and (app_id is None or r.app_id == app_id)
        ]

        if len(recent) < 2:
            return []

        anomalies: list[Anomaly] = []

        # Group by hour
        hourly_costs: dict[str, float] = {}
        hourly_tokens: dict[str, int] = {}
        hourly_errors: dict[str, int] = {}
        hourly_latencies: dict[str, list[float]] = {}

        for record in recent:
            hour_key = record.timestamp.strftime("%Y-%m-%d-%H")
            hourly_costs[hour_key] = hourly_costs.get(hour_key, 0) + record.cost_usd
            hourly_tokens[hour_key] = (
                hourly_tokens.get(hour_key, 0)
                + record.input_tokens
                + record.output_tokens
            )
            if record.error:
                hourly_errors[hour_key] = hourly_errors.get(hour_key, 0) + 1
            if hour_key not in hourly_latencies:
                hourly_latencies[hour_key] = []
            hourly_latencies[hour_key].append(record.latency_ms)

        # Detect cost spikes
        anomalies.extend(
            self._detect_spikes(hourly_costs, AnomalyType.COST_SPIKE, app_id)
        )

        # Detect token spikes
        anomalies.extend(
            self._detect_spikes(
                {k: float(v) for k, v in hourly_tokens.items()},
                AnomalyType.TOKEN_SPIKE,
                app_id,
            )
        )

        # Detect error spikes
        if hourly_errors:
            anomalies.extend(
                self._detect_spikes(
                    {k: float(v) for k, v in hourly_errors.items()},
                    AnomalyType.ERROR_SPIKE,
                    app_id,
                )
            )

        return anomalies

    async def get_governance_kpis(
        self,
        org_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> GovernanceKPIs:
        """Get governance KPIs for an organization."""
        filtered = [
            r
            for r in self._records
            if r.org_id == org_id
            and (start_date is None or r.timestamp >= start_date)
            and (end_date is None or r.timestamp <= end_date)
        ]

        if not filtered:
            return GovernanceKPIs(
                org_id=org_id,
                total_requests=0,
                allowed_requests=0,
                denied_requests=0,
                approval_rate=0.0,
                total_cost_usd=0.0,
                budget_utilization_percent=0.0,
                avg_latency_ms=0.0,
                error_rate=0.0,
            )

        total = len(filtered)
        allowed = sum(1 for r in filtered if r.allowed)
        denied = total - allowed
        errors = sum(1 for r in filtered if r.error)
        total_cost = sum(r.cost_usd for r in filtered)
        total_latency = sum(r.latency_ms for r in filtered)

        # Top models
        model_counts: dict[str, int] = {}
        for r in filtered:
            model_counts[r.model] = model_counts.get(r.model, 0) + 1
        top_models = sorted(model_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        # Top apps
        app_counts: dict[str, int] = {}
        for r in filtered:
            app_counts[r.app_id] = app_counts.get(r.app_id, 0) + 1
        top_apps = sorted(app_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        return GovernanceKPIs(
            org_id=org_id,
            total_requests=total,
            allowed_requests=allowed,
            denied_requests=denied,
            approval_rate=round(allowed / total * 100, 2),
            total_cost_usd=round(total_cost, 4),
            budget_utilization_percent=0.0,  # Would need budget info
            avg_latency_ms=round(total_latency / total, 2),
            error_rate=round(errors / total * 100, 2),
            top_models=top_models,
            top_apps=top_apps,
        )

    async def get_usage_trends(
        self,
        app_id: str,
        metric: str,
        granularity: str = "hour",
        lookback_hours: int = 24,
    ) -> list[tuple[datetime, float]]:
        """Get usage trends for an app."""
        cutoff = datetime.now() - timedelta(hours=lookback_hours)
        filtered = [
            r for r in self._records if r.app_id == app_id and r.timestamp >= cutoff
        ]

        if not filtered:
            return []

        # Format key based on granularity
        if granularity == "minute":
            format_str = "%Y-%m-%d %H:%M"
        elif granularity == "day":
            format_str = "%Y-%m-%d"
        else:  # hour
            format_str = "%Y-%m-%d %H:00"

        buckets: dict[str, float] = {}

        for record in filtered:
            key = record.timestamp.strftime(format_str)

            if metric == "requests":
                buckets[key] = buckets.get(key, 0) + 1
            elif metric == "cost":
                buckets[key] = buckets.get(key, 0) + record.cost_usd
            elif metric == "tokens":
                buckets[key] = (
                    buckets.get(key, 0) + record.input_tokens + record.output_tokens
                )
            elif metric == "latency":
                if key not in buckets:
                    buckets[key] = record.latency_ms
                else:
                    # Running average
                    buckets[key] = (buckets[key] + record.latency_ms) / 2

        # Convert to sorted list of tuples
        result: list[tuple[datetime, float]] = []
        for key in sorted(buckets.keys()):
            if granularity == "minute":
                ts = datetime.strptime(key, "%Y-%m-%d %H:%M")
            elif granularity == "day":
                ts = datetime.strptime(key, "%Y-%m-%d")
            else:
                ts = datetime.strptime(key, "%Y-%m-%d %H:00")
            result.append((ts, round(buckets[key], 4)))

        return result

    def _apply_filters(self, filters: CostFilters) -> list[UsageRecord]:
        """Apply filters to records."""
        return [
            r
            for r in self._records
            if (filters.start_date is None or r.timestamp >= filters.start_date)
            and (filters.end_date is None or r.timestamp <= filters.end_date)
            and (filters.app_id is None or r.app_id == filters.app_id)
            and (filters.org_id is None or r.org_id == filters.org_id)
            and (filters.model is None or r.model == filters.model)
            and (filters.environment is None or r.environment == filters.environment)
        ]

    def _detect_spikes(
        self,
        hourly_values: dict[str, float],
        anomaly_type: AnomalyType,
        app_id: str | None,
    ) -> list[Anomaly]:
        """Detect spikes in hourly values."""
        if len(hourly_values) < 2:
            return []

        values = list(hourly_values.values())
        avg = sum(values) / len(values)

        if avg == 0:
            return []

        anomalies: list[Anomaly] = []

        for hour_key, value in hourly_values.items():
            deviation = ((value - avg) / avg) * 100
            if deviation > self._anomaly_threshold:
                severity = (
                    AnomalySeverity.CRITICAL
                    if deviation > 200
                    else (
                        AnomalySeverity.HIGH
                        if deviation > 100
                        else AnomalySeverity.MEDIUM
                    )
                )
                anomalies.append(
                    Anomaly(
                        anomaly_id=str(uuid.uuid4()),
                        anomaly_type=anomaly_type,
                        severity=severity,
                        app_id=app_id,
                        description=f"{anomaly_type.value} detected: {deviation:.1f}% above average",
                        detected_at=datetime.now(),
                        metric_value=value,
                        expected_value=avg,
                        deviation_percent=round(deviation, 2),
                        metadata={"hour": hour_key},
                    )
                )

        return anomalies

    def clear(self) -> None:
        """Clear all records."""
        self._records.clear()
