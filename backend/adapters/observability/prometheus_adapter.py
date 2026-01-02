"""Prometheus/Grafana Observability Adapter.

Architecture Hexagonale: Implémentation production du ObservabilityPort
utilisant Prometheus pour les métriques et InfluxDB/Grafana pour l'analytics.

Ce module fournit:
- Export métriques vers Prometheus
- Queries PromQL pour analytics
- Détection d'anomalies basée sur stddev
- Agrégation de KPIs
"""

import uuid
from datetime import datetime, timedelta
from typing import Any

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


class PrometheusObservabilityAdapter(ObservabilityPort):
    """
    Prometheus-based observability implementation.

    Uses prometheus_client for metrics export and PromQL queries
    for analytics. Falls back to in-memory storage for testing.
    """

    def __init__(
        self,
        prometheus_url: str | None = None,
        push_gateway_url: str | None = None,
        metrics_prefix: str = "llm_gateway",
        http_client: Any = None,
    ):
        """
        Initialize Prometheus adapter.

        Args:
            prometheus_url: Prometheus server URL for queries
            push_gateway_url: Push Gateway URL for pushing metrics
            metrics_prefix: Prefix for all metric names
            http_client: Optional HTTP client for API calls
        """
        self._prometheus_url = prometheus_url or "http://localhost:9090"
        self._push_gateway_url = push_gateway_url
        self._prefix = metrics_prefix
        self._http_client = http_client

        # In-memory storage for testing/fallback
        self._requests: list[dict] = []
        self._anomalies: list[Anomaly] = []

        # Prometheus metrics (if prometheus_client available)
        self._metrics_initialized = False
        self._init_prometheus_metrics()

    def _init_prometheus_metrics(self) -> None:
        """Initialize Prometheus metrics if library available."""
        try:
            from prometheus_client import Counter, Histogram, Gauge

            self._request_counter = Counter(
                f"{self._prefix}_requests_total",
                "Total LLM requests",
                ["app_id", "model", "environment", "outcome"],
            )

            self._token_counter = Counter(
                f"{self._prefix}_tokens_total",
                "Total tokens processed",
                ["app_id", "model", "direction"],  # direction: input/output
            )

            self._cost_counter = Counter(
                f"{self._prefix}_cost_usd_total",
                "Total cost in USD",
                ["app_id", "model", "environment"],
            )

            self._latency_histogram = Histogram(
                f"{self._prefix}_request_latency_ms",
                "Request latency in milliseconds",
                ["app_id", "model"],
                buckets=[50, 100, 250, 500, 1000, 2500, 5000, 10000],
            )

            self._active_requests = Gauge(
                f"{self._prefix}_active_requests",
                "Currently active requests",
                ["app_id"],
            )

            self._metrics_initialized = True

        except ImportError:
            # prometheus_client not available, use in-memory only
            pass

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
        """Record request metrics to Prometheus and in-memory store."""
        now = datetime.now()

        # Store in memory for queries
        self._requests.append(
            {
                "timestamp": now,
                "app_id": app_id,
                "org_id": org_id,
                "model": model,
                "environment": environment,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost_usd,
                "latency_ms": latency_ms,
                "outcome": outcome,
                "feature": feature,
            }
        )

        # Update Prometheus metrics if available
        if self._metrics_initialized:
            self._request_counter.labels(
                app_id=app_id,
                model=model,
                environment=environment,
                outcome=outcome,
            ).inc()

            self._token_counter.labels(
                app_id=app_id,
                model=model,
                direction="input",
            ).inc(input_tokens)

            self._token_counter.labels(
                app_id=app_id,
                model=model,
                direction="output",
            ).inc(output_tokens)

            self._cost_counter.labels(
                app_id=app_id,
                model=model,
                environment=environment,
            ).inc(cost_usd)

            self._latency_histogram.labels(
                app_id=app_id,
                model=model,
            ).observe(latency_ms)

        # Check for anomalies
        await self._check_for_anomalies(app_id, cost_usd, latency_ms)

    async def get_cost_breakdown(
        self,
        filters: CostFilters,
    ) -> CostBreakdown:
        """Get cost breakdown from stored requests."""
        filtered = self._filter_requests(filters)

        total_cost = sum(r["cost_usd"] for r in filtered)
        by_model: dict[str, float] = {}
        by_app: dict[str, float] = {}
        by_environment: dict[str, float] = {}
        by_day: dict[str, float] = {}

        for req in filtered:
            model = req["model"]
            by_model[model] = by_model.get(model, 0) + req["cost_usd"]

            app = req["app_id"]
            by_app[app] = by_app.get(app, 0) + req["cost_usd"]

            env = req["environment"]
            by_environment[env] = by_environment.get(env, 0) + req["cost_usd"]

            day = req["timestamp"].strftime("%Y-%m-%d")
            by_day[day] = by_day.get(day, 0) + req["cost_usd"]

        return CostBreakdown(
            total_cost_usd=total_cost,
            by_model=by_model,
            by_app=by_app,
            by_environment=by_environment,
            by_day=by_day,
            period_start=filters.start_date,
            period_end=filters.end_date,
        )

    async def get_token_efficiency(
        self,
        app_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> TokenEfficiency:
        """Calculate token efficiency for an app."""
        filters = CostFilters(
            app_id=app_id,
            start_date=start_date,
            end_date=end_date,
        )
        filtered = self._filter_requests(filters)

        if not filtered:
            return TokenEfficiency(
                app_id=app_id,
                total_input_tokens=0,
                total_output_tokens=0,
                avg_input_per_request=0,
                avg_output_per_request=0,
                input_output_ratio=0,
                cost_per_1k_tokens=0,
            )

        total_input = sum(r["input_tokens"] for r in filtered)
        total_output = sum(r["output_tokens"] for r in filtered)
        total_cost = sum(r["cost_usd"] for r in filtered)
        count = len(filtered)

        total_tokens = total_input + total_output

        return TokenEfficiency(
            app_id=app_id,
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            avg_input_per_request=total_input / count,
            avg_output_per_request=total_output / count,
            input_output_ratio=total_input / total_output if total_output > 0 else 0,
            cost_per_1k_tokens=(
                (total_cost / total_tokens * 1000) if total_tokens > 0 else 0
            ),
        )

    async def detect_anomalies(
        self,
        app_id: str | None = None,
        lookback_hours: int = 24,
    ) -> list[Anomaly]:
        """Return detected anomalies."""
        cutoff = datetime.now() - timedelta(hours=lookback_hours)

        anomalies = [
            a
            for a in self._anomalies
            if a.detected_at >= cutoff and (app_id is None or a.app_id == app_id)
        ]

        return sorted(anomalies, key=lambda a: a.detected_at, reverse=True)

    async def get_governance_kpis(
        self,
        org_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> GovernanceKPIs:
        """Calculate governance KPIs for an org."""
        filters = CostFilters(
            org_id=org_id,
            start_date=start_date,
            end_date=end_date,
        )
        filtered = self._filter_requests(filters)

        if not filtered:
            return GovernanceKPIs(
                org_id=org_id,
                total_requests=0,
                allowed_requests=0,
                denied_requests=0,
                approval_rate=0,
                total_cost_usd=0,
                budget_utilization_percent=0,
                avg_latency_ms=0,
                error_rate=0,
            )

        total = len(filtered)
        allowed = sum(1 for r in filtered if r["outcome"] == "allowed")
        denied = sum(1 for r in filtered if r["outcome"].startswith("denied"))
        errors = sum(1 for r in filtered if r["outcome"] == "error")

        total_cost = sum(r["cost_usd"] for r in filtered)
        total_latency = sum(r["latency_ms"] for r in filtered)

        # Count by model and app
        model_counts: dict[str, int] = {}
        app_counts: dict[str, int] = {}
        for r in filtered:
            model = r["model"]
            model_counts[model] = model_counts.get(model, 0) + 1
            app = r["app_id"]
            app_counts[app] = app_counts.get(app, 0) + 1

        top_models = sorted(model_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        top_apps = sorted(app_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        return GovernanceKPIs(
            org_id=org_id,
            total_requests=total,
            allowed_requests=allowed,
            denied_requests=denied,
            approval_rate=allowed / total if total > 0 else 0,
            total_cost_usd=total_cost,
            budget_utilization_percent=0,  # Would need budget info
            avg_latency_ms=total_latency / total if total > 0 else 0,
            error_rate=errors / total if total > 0 else 0,
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
        """Get usage trends for a metric."""
        cutoff = datetime.now() - timedelta(hours=lookback_hours)
        filtered = [
            r
            for r in self._requests
            if r["app_id"] == app_id and r["timestamp"] >= cutoff
        ]

        # Group by time bucket
        buckets: dict[str, list[dict]] = {}
        for r in filtered:
            if granularity == "minute":
                key = r["timestamp"].strftime("%Y-%m-%d %H:%M")
            elif granularity == "hour":
                key = r["timestamp"].strftime("%Y-%m-%d %H:00")
            else:  # day
                key = r["timestamp"].strftime("%Y-%m-%d")

            if key not in buckets:
                buckets[key] = []
            buckets[key].append(r)

        # Calculate metric for each bucket
        results = []
        for key, reqs in sorted(buckets.items()):
            if granularity == "minute":
                ts = datetime.strptime(key, "%Y-%m-%d %H:%M")
            elif granularity == "hour":
                ts = datetime.strptime(key, "%Y-%m-%d %H:00")
            else:
                ts = datetime.strptime(key, "%Y-%m-%d")

            if metric == "requests":
                value = len(reqs)
            elif metric == "cost":
                value = sum(r["cost_usd"] for r in reqs)
            elif metric == "tokens":
                value = sum(r["input_tokens"] + r["output_tokens"] for r in reqs)
            elif metric == "latency":
                value = sum(r["latency_ms"] for r in reqs) / len(reqs)
            else:
                value = 0

            results.append((ts, value))

        return results

    def _filter_requests(self, filters: CostFilters) -> list[dict]:
        """Filter requests based on criteria."""
        result = self._requests

        if filters.start_date:
            result = [r for r in result if r["timestamp"] >= filters.start_date]
        if filters.end_date:
            result = [r for r in result if r["timestamp"] <= filters.end_date]
        if filters.app_id:
            result = [r for r in result if r["app_id"] == filters.app_id]
        if filters.org_id:
            result = [r for r in result if r["org_id"] == filters.org_id]
        if filters.model:
            result = [r for r in result if r["model"] == filters.model]
        if filters.environment:
            result = [r for r in result if r["environment"] == filters.environment]

        return result

    async def _check_for_anomalies(
        self,
        app_id: str,
        cost_usd: float,
        latency_ms: float,
    ) -> None:
        """Check if current values are anomalous."""
        # Get recent history for this app
        cutoff = datetime.now() - timedelta(hours=1)
        recent = [
            r
            for r in self._requests
            if r["app_id"] == app_id and r["timestamp"] >= cutoff
        ]

        if len(recent) < 10:
            return  # Not enough data

        # Check cost spike
        avg_cost = sum(r["cost_usd"] for r in recent) / len(recent)
        if avg_cost > 0 and cost_usd > avg_cost * 5:
            self._anomalies.append(
                Anomaly(
                    anomaly_id=f"anom_{uuid.uuid4().hex[:8]}",
                    anomaly_type=AnomalyType.COST_SPIKE,
                    severity=AnomalySeverity.HIGH,
                    app_id=app_id,
                    description=f"Cost spike: ${cost_usd:.4f} vs avg ${avg_cost:.4f}",
                    detected_at=datetime.now(),
                    metric_value=cost_usd,
                    expected_value=avg_cost,
                    deviation_percent=((cost_usd - avg_cost) / avg_cost) * 100,
                )
            )

        # Check latency spike
        avg_latency = sum(r["latency_ms"] for r in recent) / len(recent)
        if avg_latency > 0 and latency_ms > avg_latency * 3:
            self._anomalies.append(
                Anomaly(
                    anomaly_id=f"anom_{uuid.uuid4().hex[:8]}",
                    anomaly_type=AnomalyType.LATENCY_SPIKE,
                    severity=AnomalySeverity.MEDIUM,
                    app_id=app_id,
                    description=f"Latency spike: {latency_ms:.0f}ms vs avg {avg_latency:.0f}ms",
                    detected_at=datetime.now(),
                    metric_value=latency_ms,
                    expected_value=avg_latency,
                    deviation_percent=((latency_ms - avg_latency) / avg_latency) * 100,
                )
            )

    async def query_prometheus(self, query: str) -> dict:
        """Execute a PromQL query against Prometheus."""
        if not self._http_client:
            return {"status": "error", "error": "No HTTP client configured"}

        try:
            response = await self._http_client.get(
                f"{self._prometheus_url}/api/v1/query",
                params={"query": query},
            )
            return response.json()
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def clear(self) -> None:
        """Clear all stored data (for testing)."""
        self._requests.clear()
        self._anomalies.clear()
