"""Tests for InMemoryObservabilityAdapter.

Tests for cost breakdown, token efficiency, anomaly detection, and governance KPIs.
"""

import pytest
from datetime import datetime, timedelta

from backend.adapters.observability import InMemoryObservabilityAdapter
from backend.ports.observability import (
    CostFilters,
    AnomalyType,
    AnomalySeverity,
)


@pytest.fixture
def adapter():
    """Create a fresh adapter for each test."""
    return InMemoryObservabilityAdapter()


@pytest.fixture
def adapter_with_data(adapter):
    """Adapter with sample usage data."""
    now = datetime.now()

    # Add records across different dimensions
    for i in range(10):
        adapter.record_usage(
            app_id="app1",
            org_id="org1",
            model="gpt-4",
            environment="production",
            input_tokens=1000 + i * 100,
            output_tokens=500 + i * 50,
            latency_ms=100 + i * 10,
            allowed=True,
            timestamp=now - timedelta(hours=i),
        )

    for i in range(5):
        adapter.record_usage(
            app_id="app2",
            org_id="org1",
            model="gpt-3.5-turbo",
            environment="development",
            input_tokens=500,
            output_tokens=250,
            latency_ms=50,
            allowed=True,
            timestamp=now - timedelta(hours=i),
        )

    return adapter


class TestCostBreakdown:
    """Tests for cost breakdown functionality."""

    @pytest.mark.asyncio
    async def test_cost_breakdown_no_filters(self, adapter_with_data):
        """Test cost breakdown without filters."""
        filters = CostFilters()
        breakdown = await adapter_with_data.get_cost_breakdown(filters)

        assert breakdown.total_cost_usd > 0
        assert len(breakdown.by_model) == 2
        assert "gpt-4" in breakdown.by_model
        assert "gpt-3.5-turbo" in breakdown.by_model

    @pytest.mark.asyncio
    async def test_cost_breakdown_by_app(self, adapter_with_data):
        """Test cost breakdown filtered by app."""
        filters = CostFilters(app_id="app1")
        breakdown = await adapter_with_data.get_cost_breakdown(filters)

        assert len(breakdown.by_app) == 1
        assert "app1" in breakdown.by_app

    @pytest.mark.asyncio
    async def test_cost_breakdown_by_model(self, adapter_with_data):
        """Test cost breakdown filtered by model."""
        filters = CostFilters(model="gpt-4")
        breakdown = await adapter_with_data.get_cost_breakdown(filters)

        assert len(breakdown.by_model) == 1
        assert "gpt-4" in breakdown.by_model

    @pytest.mark.asyncio
    async def test_cost_breakdown_by_environment(self, adapter_with_data):
        """Test cost breakdown includes environment breakdown."""
        filters = CostFilters()
        breakdown = await adapter_with_data.get_cost_breakdown(filters)

        assert "production" in breakdown.by_environment
        assert "development" in breakdown.by_environment

    @pytest.mark.asyncio
    async def test_cost_breakdown_empty(self, adapter):
        """Test cost breakdown with no data."""
        filters = CostFilters()
        breakdown = await adapter.get_cost_breakdown(filters)

        assert breakdown.total_cost_usd == 0
        assert len(breakdown.by_model) == 0


class TestTokenEfficiency:
    """Tests for token efficiency metrics."""

    @pytest.mark.asyncio
    async def test_token_efficiency_basic(self, adapter_with_data):
        """Test basic token efficiency calculation."""
        efficiency = await adapter_with_data.get_token_efficiency("app1")

        assert efficiency.app_id == "app1"
        assert efficiency.total_input_tokens > 0
        assert efficiency.total_output_tokens > 0
        assert efficiency.avg_input_per_request > 0
        assert efficiency.avg_output_per_request > 0

    @pytest.mark.asyncio
    async def test_token_efficiency_ratio(self, adapter_with_data):
        """Test input/output ratio calculation."""
        efficiency = await adapter_with_data.get_token_efficiency("app1")

        expected_ratio = efficiency.total_input_tokens / max(efficiency.total_output_tokens, 1)
        assert abs(efficiency.input_output_ratio - expected_ratio) < 0.01

    @pytest.mark.asyncio
    async def test_token_efficiency_nonexistent_app(self, adapter_with_data):
        """Test efficiency for app with no data."""
        efficiency = await adapter_with_data.get_token_efficiency("nonexistent")

        assert efficiency.total_input_tokens == 0
        assert efficiency.total_output_tokens == 0
        assert efficiency.cost_per_1k_tokens == 0


class TestAnomalyDetection:
    """Tests for anomaly detection."""

    @pytest.mark.asyncio
    async def test_detect_cost_spike(self, adapter):
        """Test detection of cost spikes."""
        now = datetime.now()

        # Normal usage for several hours
        for i in range(5):
            adapter.record_usage(
                app_id="app1",
                org_id="org1",
                model="gpt-4",
                environment="production",
                input_tokens=1000,
                output_tokens=500,
                latency_ms=100,
                allowed=True,
                timestamp=now - timedelta(hours=5 - i),
            )

        # Spike in the last hour (10x normal)
        for i in range(10):
            adapter.record_usage(
                app_id="app1",
                org_id="org1",
                model="gpt-4",
                environment="production",
                input_tokens=10000,
                output_tokens=5000,
                latency_ms=100,
                allowed=True,
                timestamp=now,
            )

        anomalies = await adapter.detect_anomalies(app_id="app1", lookback_hours=6)

        # Should detect cost or token spike
        spike_types = [a.anomaly_type for a in anomalies]
        assert AnomalyType.COST_SPIKE in spike_types or AnomalyType.TOKEN_SPIKE in spike_types

    @pytest.mark.asyncio
    async def test_no_anomalies_with_normal_usage(self, adapter):
        """Test no anomalies detected with consistent usage."""
        now = datetime.now()

        # Consistent usage across hours
        for i in range(6):
            adapter.record_usage(
                app_id="app1",
                org_id="org1",
                model="gpt-4",
                environment="production",
                input_tokens=1000,
                output_tokens=500,
                latency_ms=100,
                allowed=True,
                timestamp=now - timedelta(hours=i),
            )

        anomalies = await adapter.detect_anomalies(app_id="app1", lookback_hours=6)

        # No significant spikes expected
        assert len(anomalies) == 0

    @pytest.mark.asyncio
    async def test_anomaly_severity(self, adapter):
        """Test anomaly severity classification."""
        now = datetime.now()

        # Create a massive spike (> 200% deviation)
        for i in range(3):
            adapter.record_usage(
                app_id="app1",
                org_id="org1",
                model="gpt-4",
                environment="production",
                input_tokens=100,
                output_tokens=50,
                latency_ms=100,
                allowed=True,
                timestamp=now - timedelta(hours=3 - i),
            )

        # Massive spike
        for i in range(50):
            adapter.record_usage(
                app_id="app1",
                org_id="org1",
                model="gpt-4",
                environment="production",
                input_tokens=10000,
                output_tokens=5000,
                latency_ms=100,
                allowed=True,
                timestamp=now,
            )

        anomalies = await adapter.detect_anomalies(app_id="app1", lookback_hours=4)

        if anomalies:
            # Large spikes should be HIGH or CRITICAL
            assert any(
                a.severity in (AnomalySeverity.HIGH, AnomalySeverity.CRITICAL) for a in anomalies
            )


class TestGovernanceKPIs:
    """Tests for governance KPIs."""

    @pytest.mark.asyncio
    async def test_governance_kpis_basic(self, adapter_with_data):
        """Test basic governance KPIs."""
        kpis = await adapter_with_data.get_governance_kpis("org1")

        assert kpis.org_id == "org1"
        assert kpis.total_requests == 15  # 10 + 5
        assert kpis.allowed_requests == 15
        assert kpis.denied_requests == 0
        assert kpis.approval_rate == 100.0

    @pytest.mark.asyncio
    async def test_governance_kpis_with_denials(self, adapter):
        """Test KPIs with some denied requests."""
        now = datetime.now()

        # 7 allowed, 3 denied
        for i in range(7):
            adapter.record_usage(
                app_id="app1",
                org_id="org1",
                model="gpt-4",
                environment="production",
                input_tokens=1000,
                output_tokens=500,
                latency_ms=100,
                allowed=True,
                timestamp=now,
            )

        for i in range(3):
            adapter.record_usage(
                app_id="app1",
                org_id="org1",
                model="gpt-4",
                environment="production",
                input_tokens=1000,
                output_tokens=500,
                latency_ms=100,
                allowed=False,
                timestamp=now,
            )

        kpis = await adapter.get_governance_kpis("org1")

        assert kpis.total_requests == 10
        assert kpis.allowed_requests == 7
        assert kpis.denied_requests == 3
        assert kpis.approval_rate == 70.0

    @pytest.mark.asyncio
    async def test_governance_kpis_top_models(self, adapter_with_data):
        """Test top models ranking."""
        kpis = await adapter_with_data.get_governance_kpis("org1")

        assert len(kpis.top_models) > 0
        # gpt-4 has more requests
        assert kpis.top_models[0][0] == "gpt-4"

    @pytest.mark.asyncio
    async def test_governance_kpis_empty_org(self, adapter):
        """Test KPIs for org with no data."""
        kpis = await adapter.get_governance_kpis("nonexistent")

        assert kpis.total_requests == 0
        assert kpis.approval_rate == 0


class TestUsageTrends:
    """Tests for usage trends."""

    @pytest.mark.asyncio
    async def test_usage_trends_requests(self, adapter_with_data):
        """Test request count trends."""
        trends = await adapter_with_data.get_usage_trends(
            app_id="app1",
            metric="requests",
            granularity="hour",
            lookback_hours=24,
        )

        assert len(trends) > 0
        # Each entry is (timestamp, value)
        for ts, value in trends:
            assert isinstance(ts, datetime)
            assert value >= 1

    @pytest.mark.asyncio
    async def test_usage_trends_cost(self, adapter_with_data):
        """Test cost trends."""
        trends = await adapter_with_data.get_usage_trends(
            app_id="app1",
            metric="cost",
            granularity="hour",
            lookback_hours=24,
        )

        assert len(trends) > 0
        for ts, value in trends:
            assert value > 0

    @pytest.mark.asyncio
    async def test_usage_trends_granularity(self, adapter_with_data):
        """Test different granularities."""
        hourly = await adapter_with_data.get_usage_trends(
            app_id="app1",
            metric="requests",
            granularity="hour",
            lookback_hours=24,
        )

        daily = await adapter_with_data.get_usage_trends(
            app_id="app1",
            metric="requests",
            granularity="day",
            lookback_hours=24,
        )

        # Daily should have fewer entries
        assert len(daily) <= len(hourly)


class TestAdapterManagement:
    """Tests for adapter management."""

    def test_record_usage(self, adapter):
        """Test recording usage."""
        adapter.record_usage(
            app_id="app1",
            org_id="org1",
            model="gpt-4",
            environment="production",
            input_tokens=1000,
            output_tokens=500,
            latency_ms=100,
            allowed=True,
        )

        assert len(adapter._records) == 1

    def test_clear(self, adapter_with_data):
        """Test clearing records."""
        assert len(adapter_with_data._records) > 0

        adapter_with_data.clear()

        assert len(adapter_with_data._records) == 0
