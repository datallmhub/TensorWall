"""Tests unitaires pour les adapters de métriques.

Ces tests vérifient que les adapters de métriques (Prometheus, InMemory)
implémentent correctement l'interface MetricsPort.
"""

import pytest

from backend.adapters.prometheus import PrometheusMetricsAdapter, InMemoryMetricsAdapter
from backend.ports.metrics import (
    MetricsPort,
    RequestMetrics,
    DecisionMetrics,
    BudgetMetrics,
)


# =============================================================================
# Tests InMemoryMetricsAdapter
# =============================================================================


class TestInMemoryMetricsAdapter:
    """Tests pour l'adapter InMemory (utilisé pour les tests)."""

    def test_implements_port(self):
        """Vérifie que l'adapter implémente le port."""
        adapter = InMemoryMetricsAdapter()
        assert isinstance(adapter, MetricsPort)

    def test_record_request(self):
        """Vérifie l'enregistrement d'une requête."""
        adapter = InMemoryMetricsAdapter()

        metrics = RequestMetrics(
            app_id="test-app",
            model="gpt-4",
            status="success",
            latency_seconds=1.5,
            feature="chat",
            environment="production",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.005,
        )

        adapter.record_request(metrics)

        assert len(adapter.requests) == 1
        assert adapter.requests[0].app_id == "test-app"
        assert adapter.requests[0].latency_seconds == 1.5

    def test_record_decision(self):
        """Vérifie l'enregistrement d'une décision."""
        adapter = InMemoryMetricsAdapter()

        metrics = DecisionMetrics(
            app_id="test-app",
            decision="deny",
            source="policy",
        )

        adapter.record_decision(metrics)

        assert len(adapter.decisions) == 1
        assert adapter.decisions[0].decision == "deny"

    def test_record_error(self):
        """Vérifie l'enregistrement d'une erreur."""
        adapter = InMemoryMetricsAdapter()

        adapter.record_error("test-app", "timeout")

        assert len(adapter.errors) == 1
        assert adapter.errors[0] == ("test-app", "timeout")

    def test_record_security_block(self):
        """Vérifie l'enregistrement d'un blocage de sécurité."""
        adapter = InMemoryMetricsAdapter()

        adapter.record_security_block("test-app", "injection_attempt")

        assert len(adapter.security_blocks) == 1
        assert adapter.security_blocks[0] == ("test-app", "injection_attempt")

    def test_update_budget(self):
        """Vérifie la mise à jour des métriques de budget."""
        adapter = InMemoryMetricsAdapter()

        metrics = BudgetMetrics(
            app_id="test-app",
            feature="chat",
            environment="production",
            usage_ratio=0.75,
            remaining_usd=250.0,
        )

        adapter.update_budget(metrics)

        key = "test-app:chat:production"
        assert key in adapter.budgets
        assert adapter.budgets[key].usage_ratio == 0.75

    def test_request_started_and_finished(self):
        """Vérifie le suivi des requêtes actives."""
        adapter = InMemoryMetricsAdapter()

        adapter.request_started("app-1")
        adapter.request_started("app-1")
        adapter.request_started("app-2")

        assert adapter.active_requests["app-1"] == 2
        assert adapter.active_requests["app-2"] == 1

        adapter.request_finished("app-1")

        assert adapter.active_requests["app-1"] == 1

    def test_request_finished_never_negative(self):
        """Vérifie que le compteur de requêtes actives ne devient pas négatif."""
        adapter = InMemoryMetricsAdapter()

        adapter.request_finished("app-1")
        adapter.request_finished("app-1")

        assert adapter.active_requests["app-1"] == 0

    def test_clear(self):
        """Vérifie le vidage des métriques."""
        adapter = InMemoryMetricsAdapter()

        adapter.record_request(
            RequestMetrics(app_id="app-1", model="gpt-4", status="success", latency_seconds=1.0)
        )
        adapter.record_error("app-1", "error")
        adapter.request_started("app-1")

        adapter.clear()

        assert len(adapter.requests) == 0
        assert len(adapter.errors) == 0
        assert len(adapter.active_requests) == 0

    def test_get_request_count_no_filter(self):
        """Vérifie le comptage des requêtes sans filtre."""
        adapter = InMemoryMetricsAdapter()

        for i in range(5):
            adapter.record_request(
                RequestMetrics(
                    app_id=f"app-{i % 2}",
                    model="gpt-4",
                    status="success" if i % 2 == 0 else "error",
                    latency_seconds=1.0,
                )
            )

        assert adapter.get_request_count() == 5

    def test_get_request_count_with_filters(self):
        """Vérifie le comptage des requêtes avec filtres."""
        adapter = InMemoryMetricsAdapter()

        adapter.record_request(
            RequestMetrics(app_id="app-1", model="gpt-4", status="success", latency_seconds=1.0)
        )
        adapter.record_request(
            RequestMetrics(app_id="app-1", model="gpt-4", status="error", latency_seconds=1.0)
        )
        adapter.record_request(
            RequestMetrics(app_id="app-2", model="gpt-4", status="success", latency_seconds=1.0)
        )

        assert adapter.get_request_count(app_id="app-1") == 2
        assert adapter.get_request_count(status="success") == 2
        assert adapter.get_request_count(app_id="app-1", status="error") == 1

    def test_get_decision_count(self):
        """Vérifie le comptage des décisions."""
        adapter = InMemoryMetricsAdapter()

        adapter.record_decision(DecisionMetrics(app_id="app-1", decision="allow", source="policy"))
        adapter.record_decision(DecisionMetrics(app_id="app-1", decision="deny", source="budget"))
        adapter.record_decision(DecisionMetrics(app_id="app-2", decision="deny", source="policy"))

        assert adapter.get_decision_count() == 3
        assert adapter.get_decision_count(decision="deny") == 2
        assert adapter.get_decision_count(source="policy") == 2

    def test_get_total_tokens(self):
        """Vérifie le calcul du total des tokens."""
        adapter = InMemoryMetricsAdapter()

        adapter.record_request(
            RequestMetrics(
                app_id="app-1",
                model="gpt-4",
                status="success",
                latency_seconds=1.0,
                input_tokens=100,
                output_tokens=50,
            )
        )
        adapter.record_request(
            RequestMetrics(
                app_id="app-1",
                model="gpt-4",
                status="success",
                latency_seconds=1.0,
                input_tokens=200,
                output_tokens=100,
            )
        )

        assert adapter.get_total_tokens() == 450  # 100+50+200+100
        assert adapter.get_total_tokens(direction="input") == 300
        assert adapter.get_total_tokens(direction="output") == 150

    def test_get_total_cost(self):
        """Vérifie le calcul du coût total."""
        adapter = InMemoryMetricsAdapter()

        adapter.record_request(
            RequestMetrics(
                app_id="app-1",
                model="gpt-4",
                status="success",
                latency_seconds=1.0,
                cost_usd=0.01,
            )
        )
        adapter.record_request(
            RequestMetrics(
                app_id="app-1",
                model="gpt-4",
                status="success",
                latency_seconds=1.0,
                cost_usd=0.02,
            )
        )

        assert adapter.get_total_cost() == pytest.approx(0.03)

    def test_export(self):
        """Vérifie l'export des métriques."""
        adapter = InMemoryMetricsAdapter()

        adapter.record_request(
            RequestMetrics(app_id="app-1", model="gpt-4", status="success", latency_seconds=1.0)
        )
        adapter.record_error("app-1", "timeout")

        output = adapter.export()

        assert "requests_count: 1" in output
        assert "errors_count: 1" in output


# =============================================================================
# Tests PrometheusMetricsAdapter
# =============================================================================


class TestPrometheusMetricsAdapter:
    """Tests pour l'adapter Prometheus."""

    def test_implements_port(self):
        """Vérifie que l'adapter implémente le port."""
        adapter = PrometheusMetricsAdapter()
        assert isinstance(adapter, MetricsPort)

    def test_record_request_increments_counter(self):
        """Vérifie que record_request incrémente les compteurs."""
        adapter = PrometheusMetricsAdapter()

        metrics = RequestMetrics(
            app_id="test-app",
            model="gpt-4",
            status="success",
            latency_seconds=1.5,
            feature="chat",
            environment="production",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.005,
        )

        adapter.record_request(metrics)

        # Vérifier le compteur de requêtes
        assert (
            adapter.requests_total.get(
                app_id="test-app",
                feature="chat",
                model="gpt-4",
                environment="production",
                status="success",
            )
            == 1
        )

    def test_record_request_observes_latency(self):
        """Vérifie que record_request enregistre la latence."""
        adapter = PrometheusMetricsAdapter()

        metrics = RequestMetrics(
            app_id="test-app",
            model="gpt-4",
            status="success",
            latency_seconds=1.5,
        )

        adapter.record_request(metrics)

        # Vérifier que l'histogramme a des observations
        label_key = ("test-app", "gpt-4")
        assert label_key in adapter.request_latency.observations
        assert adapter.request_latency.observations[label_key] == [1.5]

    def test_record_request_tracks_tokens(self):
        """Vérifie que record_request compte les tokens."""
        adapter = PrometheusMetricsAdapter()

        metrics = RequestMetrics(
            app_id="test-app",
            model="gpt-4",
            status="success",
            latency_seconds=1.0,
            input_tokens=100,
            output_tokens=50,
        )

        adapter.record_request(metrics)

        assert adapter.tokens_total.get(app_id="test-app", model="gpt-4", direction="input") == 100
        assert adapter.tokens_total.get(app_id="test-app", model="gpt-4", direction="output") == 50

    def test_record_decision(self):
        """Vérifie que record_decision incrémente le compteur."""
        adapter = PrometheusMetricsAdapter()

        metrics = DecisionMetrics(
            app_id="test-app",
            decision="deny",
            source="policy",
        )

        adapter.record_decision(metrics)

        assert adapter.decisions_total.get(app_id="test-app", decision="deny", source="policy") == 1

    def test_record_error(self):
        """Vérifie que record_error incrémente le compteur."""
        adapter = PrometheusMetricsAdapter()

        adapter.record_error("test-app", "timeout")

        assert adapter.errors_total.get(app_id="test-app", error_type="timeout") == 1

    def test_record_security_block(self):
        """Vérifie que record_security_block incrémente le compteur."""
        adapter = PrometheusMetricsAdapter()

        adapter.record_security_block("test-app", "injection")

        assert adapter.security_blocks.get(app_id="test-app", reason="injection") == 1

    def test_update_budget(self):
        """Vérifie que update_budget met à jour les gauges."""
        adapter = PrometheusMetricsAdapter()

        metrics = BudgetMetrics(
            app_id="test-app",
            feature="chat",
            environment="production",
            usage_ratio=0.75,
            remaining_usd=250.0,
        )

        adapter.update_budget(metrics)

        assert (
            adapter.budget_usage.get(app_id="test-app", feature="chat", environment="production")
            == 0.75
        )
        assert (
            adapter.budget_remaining.get(
                app_id="test-app", feature="chat", environment="production"
            )
            == 250.0
        )

    def test_active_requests(self):
        """Vérifie le suivi des requêtes actives."""
        adapter = PrometheusMetricsAdapter()

        adapter.request_started("app-1")
        adapter.request_started("app-1")

        assert adapter.active_requests.get(app_id="app-1") == 2

        adapter.request_finished("app-1")

        assert adapter.active_requests.get(app_id="app-1") == 1

    def test_export_prometheus_format(self):
        """Vérifie l'export au format Prometheus."""
        adapter = PrometheusMetricsAdapter()

        adapter.record_request(
            RequestMetrics(
                app_id="test-app",
                model="gpt-4",
                status="success",
                latency_seconds=1.5,
                feature="chat",
                environment="production",
            )
        )

        output = adapter.export()

        # Vérifier le format Prometheus
        assert "# HELP llm_gateway_requests_total" in output
        assert "# TYPE llm_gateway_requests_total counter" in output
        assert "llm_gateway_requests_total{" in output
        assert 'app_id="test-app"' in output

    def test_export_empty_when_no_data(self):
        """Vérifie que l'export est vide quand il n'y a pas de données."""
        adapter = PrometheusMetricsAdapter()

        output = adapter.export()

        assert output == ""

    def test_multiple_requests_accumulate(self):
        """Vérifie que les requêtes multiples s'accumulent."""
        adapter = PrometheusMetricsAdapter()

        for _ in range(5):
            adapter.record_request(
                RequestMetrics(
                    app_id="test-app",
                    model="gpt-4",
                    status="success",
                    latency_seconds=1.0,
                    feature="chat",
                    environment="production",
                )
            )

        assert (
            adapter.requests_total.get(
                app_id="test-app",
                feature="chat",
                model="gpt-4",
                environment="production",
                status="success",
            )
            == 5
        )


# =============================================================================
# Tests Counter, Gauge, Histogram
# =============================================================================


class TestPrometheusMetricTypes:
    """Tests pour les types de métriques Prometheus."""

    def test_counter_export_format(self):
        """Vérifie le format d'export du Counter."""
        from backend.adapters.prometheus.metrics_adapter import Counter

        counter = Counter("test_counter", "A test counter", ["label1", "label2"])
        counter.inc(5, label1="a", label2="b")

        output = counter.export()

        assert "# HELP test_counter A test counter" in output
        assert "# TYPE test_counter counter" in output
        assert 'test_counter{label1="a",label2="b"} 5' in output

    def test_gauge_export_format(self):
        """Vérifie le format d'export du Gauge."""
        from backend.adapters.prometheus.metrics_adapter import Gauge

        gauge = Gauge("test_gauge", "A test gauge", ["app"])
        gauge.set(42.5, app="myapp")

        output = gauge.export()

        assert "# HELP test_gauge A test gauge" in output
        assert "# TYPE test_gauge gauge" in output
        assert 'test_gauge{app="myapp"} 42.5' in output

    def test_histogram_export_format(self):
        """Vérifie le format d'export du Histogram."""
        from backend.adapters.prometheus.metrics_adapter import Histogram

        histogram = Histogram(
            "test_histogram",
            "A test histogram",
            ["app"],
            buckets=(0.1, 0.5, 1.0),
        )
        histogram.observe(0.3, app="myapp")
        histogram.observe(0.7, app="myapp")

        output = histogram.export()

        assert "# HELP test_histogram A test histogram" in output
        assert "# TYPE test_histogram histogram" in output
        assert 'test_histogram_bucket{app="myapp",le="0.1"} 0' in output
        assert 'test_histogram_bucket{app="myapp",le="0.5"} 1' in output
        assert 'test_histogram_bucket{app="myapp",le="1.0"} 2' in output
        assert 'test_histogram_bucket{app="myapp",le="+Inf"} 2' in output
        assert 'test_histogram_sum{app="myapp"} 1.0' in output
        assert 'test_histogram_count{app="myapp"} 2' in output
