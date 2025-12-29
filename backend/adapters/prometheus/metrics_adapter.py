"""Prometheus Metrics Adapter - Implémentation native.

Architecture Hexagonale: Adapter natif qui implémente directement
l'interface MetricsPort pour exporter les métriques au format Prometheus.
"""

from collections import defaultdict

from backend.ports.metrics import (
    MetricsPort,
    RequestMetrics,
    DecisionMetrics,
    BudgetMetrics,
)


# =============================================================================
# Prometheus Metric Types (natifs, sans dépendance)
# =============================================================================


class Counter:
    """Prometheus-style counter metric."""

    def __init__(self, name: str, description: str, labels: list[str] | None = None):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self.values: dict[tuple, float] = defaultdict(float)

    def inc(self, value: float = 1, **labels) -> None:
        """Increment counter."""
        label_key = tuple(labels.get(k, "") for k in self.label_names)
        self.values[label_key] += value

    def get(self, **labels) -> float:
        """Get counter value."""
        label_key = tuple(labels.get(k, "") for k in self.label_names)
        return self.values.get(label_key, 0)

    def export(self) -> str:
        """Export in Prometheus format."""
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} counter",
        ]
        for label_key, value in self.values.items():
            if self.label_names:
                labels_str = ",".join(f'{k}="{v}"' for k, v in zip(self.label_names, label_key))
                lines.append(f"{self.name}{{{labels_str}}} {value}")
            else:
                lines.append(f"{self.name} {value}")
        return "\n".join(lines)


class Gauge:
    """Prometheus-style gauge metric."""

    def __init__(self, name: str, description: str, labels: list[str] | None = None):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self.values: dict[tuple, float] = {}

    def set(self, value: float, **labels) -> None:
        """Set gauge value."""
        label_key = tuple(labels.get(k, "") for k in self.label_names)
        self.values[label_key] = value

    def inc(self, value: float = 1, **labels) -> None:
        """Increment gauge."""
        label_key = tuple(labels.get(k, "") for k in self.label_names)
        self.values[label_key] = self.values.get(label_key, 0) + value

    def dec(self, value: float = 1, **labels) -> None:
        """Decrement gauge."""
        label_key = tuple(labels.get(k, "") for k in self.label_names)
        self.values[label_key] = self.values.get(label_key, 0) - value

    def get(self, **labels) -> float:
        """Get gauge value."""
        label_key = tuple(labels.get(k, "") for k in self.label_names)
        return self.values.get(label_key, 0)

    def export(self) -> str:
        """Export in Prometheus format."""
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} gauge",
        ]
        for label_key, value in self.values.items():
            if self.label_names:
                labels_str = ",".join(f'{k}="{v}"' for k, v in zip(self.label_names, label_key))
                lines.append(f"{self.name}{{{labels_str}}} {value}")
            else:
                lines.append(f"{self.name} {value}")
        return "\n".join(lines)


class Histogram:
    """Prometheus-style histogram metric."""

    DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10)

    def __init__(
        self,
        name: str,
        description: str,
        labels: list[str] | None = None,
        buckets: tuple | None = None,
    ):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self.buckets = buckets or self.DEFAULT_BUCKETS
        self.observations: dict[tuple, list[float]] = defaultdict(list)

    def observe(self, value: float, **labels) -> None:
        """Observe a value."""
        label_key = tuple(labels.get(k, "") for k in self.label_names)
        self.observations[label_key].append(value)

    def export(self) -> str:
        """Export in Prometheus format."""
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} histogram",
        ]

        for label_key, values in self.observations.items():
            labels_str = ""
            if self.label_names:
                labels_str = ",".join(f'{k}="{v}"' for k, v in zip(self.label_names, label_key))

            sorted_values = sorted(values)
            total = len(values)
            sum_val = sum(values)

            for bucket in self.buckets:
                count = sum(1 for v in sorted_values if v <= bucket)
                if labels_str:
                    lines.append(f'{self.name}_bucket{{{labels_str},le="{bucket}"}} {count}')
                else:
                    lines.append(f'{self.name}_bucket{{le="{bucket}"}} {count}')

            if labels_str:
                lines.append(f'{self.name}_bucket{{{labels_str},le="+Inf"}} {total}')
                lines.append(f"{self.name}_sum{{{labels_str}}} {sum_val}")
                lines.append(f"{self.name}_count{{{labels_str}}} {total}")
            else:
                lines.append(f'{self.name}_bucket{{le="+Inf"}} {total}')
                lines.append(f"{self.name}_sum {sum_val}")
                lines.append(f"{self.name}_count {total}")

        return "\n".join(lines)


# =============================================================================
# Prometheus Metrics Adapter
# =============================================================================


class PrometheusMetricsAdapter(MetricsPort):
    """Adapter natif pour les métriques Prometheus.

    Implémente directement l'interface MetricsPort en utilisant
    des structures de données natives pour les métriques Prometheus.
    Aucune dépendance au code legacy (exporters/).
    """

    def __init__(self):
        """Initialise les métriques Prometheus."""
        # Request metrics
        self.requests_total = Counter(
            "llm_gateway_requests_total",
            "Total number of LLM requests",
            ["app_id", "feature", "model", "environment", "status"],
        )

        self.request_latency = Histogram(
            "llm_gateway_request_latency_seconds",
            "Request latency in seconds",
            ["app_id", "model"],
            buckets=(0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60),
        )

        # Token metrics
        self.tokens_total = Counter(
            "llm_gateway_tokens_total",
            "Total tokens processed",
            ["app_id", "model", "direction"],
        )

        # Cost metrics
        self.cost_total = Counter(
            "llm_gateway_cost_usd_total",
            "Total cost in USD",
            ["app_id", "feature", "model"],
        )

        # Budget metrics
        self.budget_usage = Gauge(
            "llm_gateway_budget_usage_ratio",
            "Budget usage ratio (0-1)",
            ["app_id", "feature", "environment"],
        )

        self.budget_remaining = Gauge(
            "llm_gateway_budget_remaining_usd",
            "Remaining budget in USD",
            ["app_id", "feature", "environment"],
        )

        # Decision metrics
        self.decisions_total = Counter(
            "llm_gateway_decisions_total",
            "Total governance decisions",
            ["app_id", "decision", "source"],
        )

        # Security metrics
        self.security_blocks = Counter(
            "llm_gateway_security_blocks_total",
            "Security blocks",
            ["app_id", "reason"],
        )

        # Error metrics
        self.errors_total = Counter(
            "llm_gateway_errors_total",
            "Total errors",
            ["app_id", "error_type"],
        )

        # Active requests gauge
        self.active_requests = Gauge(
            "llm_gateway_active_requests",
            "Currently active requests",
            ["app_id"],
        )

    def record_request(self, metrics: RequestMetrics) -> None:
        """Enregistre les métriques d'une requête."""
        self.requests_total.inc(
            app_id=metrics.app_id,
            feature=metrics.feature,
            model=metrics.model,
            environment=metrics.environment,
            status=metrics.status,
        )

        self.request_latency.observe(
            metrics.latency_seconds,
            app_id=metrics.app_id,
            model=metrics.model,
        )

        if metrics.input_tokens > 0:
            self.tokens_total.inc(
                metrics.input_tokens,
                app_id=metrics.app_id,
                model=metrics.model,
                direction="input",
            )

        if metrics.output_tokens > 0:
            self.tokens_total.inc(
                metrics.output_tokens,
                app_id=metrics.app_id,
                model=metrics.model,
                direction="output",
            )

        if metrics.cost_usd > 0:
            self.cost_total.inc(
                metrics.cost_usd,
                app_id=metrics.app_id,
                feature=metrics.feature,
                model=metrics.model,
            )

    def record_decision(self, metrics: DecisionMetrics) -> None:
        """Enregistre une décision de gouvernance."""
        self.decisions_total.inc(
            app_id=metrics.app_id,
            decision=metrics.decision,
            source=metrics.source,
        )

    def record_error(self, app_id: str, error_type: str) -> None:
        """Enregistre une erreur."""
        self.errors_total.inc(app_id=app_id, error_type=error_type)

    def record_security_block(self, app_id: str, reason: str) -> None:
        """Enregistre un blocage de sécurité."""
        self.security_blocks.inc(app_id=app_id, reason=reason)

    def update_budget(self, metrics: BudgetMetrics) -> None:
        """Met à jour les métriques de budget."""
        self.budget_usage.set(
            metrics.usage_ratio,
            app_id=metrics.app_id,
            feature=metrics.feature,
            environment=metrics.environment,
        )
        self.budget_remaining.set(
            metrics.remaining_usd,
            app_id=metrics.app_id,
            feature=metrics.feature,
            environment=metrics.environment,
        )

    def request_started(self, app_id: str) -> None:
        """Signale le début d'une requête."""
        self.active_requests.inc(app_id=app_id)

    def request_finished(self, app_id: str) -> None:
        """Signale la fin d'une requête."""
        self.active_requests.dec(app_id=app_id)

    def export(self) -> str:
        """Exporte les métriques au format Prometheus."""
        metrics = [
            self.requests_total,
            self.request_latency,
            self.tokens_total,
            self.cost_total,
            self.budget_usage,
            self.budget_remaining,
            self.decisions_total,
            self.security_blocks,
            self.errors_total,
            self.active_requests,
        ]

        def has_data(m):
            if hasattr(m, "observations"):
                return bool(m.observations)
            if hasattr(m, "values"):
                return bool(m.values)
            return False

        return "\n\n".join(m.export() for m in metrics if has_data(m))


# =============================================================================
# InMemory Metrics Adapter (pour les tests)
# =============================================================================


class InMemoryMetricsAdapter(MetricsPort):
    """Adapter en mémoire pour les métriques (pour les tests).

    Stocke les métriques dans des structures simples pour
    faciliter les assertions dans les tests.
    """

    def __init__(self):
        """Initialise le stockage en mémoire."""
        self.requests: list[RequestMetrics] = []
        self.decisions: list[DecisionMetrics] = []
        self.errors: list[tuple[str, str]] = []  # (app_id, error_type)
        self.security_blocks: list[tuple[str, str]] = []  # (app_id, reason)
        self.budgets: dict[str, BudgetMetrics] = {}  # key = f"{app_id}:{feature}:{env}"
        self.active_requests: dict[str, int] = defaultdict(int)

    def record_request(self, metrics: RequestMetrics) -> None:
        """Enregistre les métriques d'une requête."""
        self.requests.append(metrics)

    def record_decision(self, metrics: DecisionMetrics) -> None:
        """Enregistre une décision de gouvernance."""
        self.decisions.append(metrics)

    def record_error(self, app_id: str, error_type: str) -> None:
        """Enregistre une erreur."""
        self.errors.append((app_id, error_type))

    def record_security_block(self, app_id: str, reason: str) -> None:
        """Enregistre un blocage de sécurité."""
        self.security_blocks.append((app_id, reason))

    def update_budget(self, metrics: BudgetMetrics) -> None:
        """Met à jour les métriques de budget."""
        key = f"{metrics.app_id}:{metrics.feature}:{metrics.environment}"
        self.budgets[key] = metrics

    def request_started(self, app_id: str) -> None:
        """Signale le début d'une requête."""
        self.active_requests[app_id] += 1

    def request_finished(self, app_id: str) -> None:
        """Signale la fin d'une requête."""
        self.active_requests[app_id] = max(0, self.active_requests[app_id] - 1)

    def export(self) -> str:
        """Exporte les métriques (format simplifié pour debug)."""
        lines = [
            f"requests_count: {len(self.requests)}",
            f"decisions_count: {len(self.decisions)}",
            f"errors_count: {len(self.errors)}",
            f"security_blocks_count: {len(self.security_blocks)}",
            f"budgets_count: {len(self.budgets)}",
            f"active_requests: {dict(self.active_requests)}",
        ]
        return "\n".join(lines)

    def clear(self) -> None:
        """Vide toutes les métriques."""
        self.requests.clear()
        self.decisions.clear()
        self.errors.clear()
        self.security_blocks.clear()
        self.budgets.clear()
        self.active_requests.clear()

    # Helpers pour les tests
    def get_request_count(self, app_id: str | None = None, status: str | None = None) -> int:
        """Compte les requêtes avec filtres optionnels."""
        filtered = self.requests
        if app_id:
            filtered = [r for r in filtered if r.app_id == app_id]
        if status:
            filtered = [r for r in filtered if r.status == status]
        return len(filtered)

    def get_decision_count(self, decision: str | None = None, source: str | None = None) -> int:
        """Compte les décisions avec filtres optionnels."""
        filtered = self.decisions
        if decision:
            filtered = [d for d in filtered if d.decision == decision]
        if source:
            filtered = [d for d in filtered if d.source == source]
        return len(filtered)

    def get_total_tokens(self, direction: str | None = None) -> int:
        """Calcule le total des tokens."""
        total = 0
        for r in self.requests:
            if direction == "input" or direction is None:
                total += r.input_tokens
            if direction == "output" or direction is None:
                total += r.output_tokens
        return total

    def get_total_cost(self) -> float:
        """Calcule le coût total."""
        return sum(r.cost_usd for r in self.requests)
