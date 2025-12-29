"""Tests for InMemoryRequestTracingAdapter.

Tests for trace creation, span management, and trace querying.
"""

import pytest

from backend.adapters.tracing import InMemoryRequestTracingAdapter
from backend.ports.request_tracing import (
    TraceFilters,
    TraceStatus,
    TraceStep,
)


@pytest.fixture
def adapter():
    """Create a fresh adapter for each test."""
    return InMemoryRequestTracingAdapter()


class TestTraceCreation:
    """Tests for trace creation."""

    @pytest.mark.asyncio
    async def test_create_trace(self, adapter):
        """Test creating a basic trace."""
        trace = await adapter.create_trace(
            request_id="req-123",
            app_id="app1",
            org_id="org1",
            model="gpt-4",
        )

        assert trace.trace_id is not None
        assert trace.request_id == "req-123"
        assert trace.app_id == "app1"
        assert trace.org_id == "org1"
        assert trace.model == "gpt-4"
        assert trace.status == TraceStatus.STARTED

    @pytest.mark.asyncio
    async def test_create_trace_with_context(self, adapter):
        """Test creating a trace with context."""
        trace = await adapter.create_trace(
            request_id="req-123",
            app_id="app1",
            context={"user_id": "user1", "feature": "chat"},
        )

        assert trace.context["user_id"] == "user1"
        assert trace.context["feature"] == "chat"

    @pytest.mark.asyncio
    async def test_get_trace(self, adapter):
        """Test getting a trace by ID."""
        created = await adapter.create_trace(
            request_id="req-123",
            app_id="app1",
        )

        retrieved = await adapter.get_trace(created.trace_id)

        assert retrieved is not None
        assert retrieved.trace_id == created.trace_id

    @pytest.mark.asyncio
    async def test_get_trace_not_found(self, adapter):
        """Test getting a non-existent trace."""
        trace = await adapter.get_trace("nonexistent")

        assert trace is None


class TestSpanManagement:
    """Tests for span management."""

    @pytest.mark.asyncio
    async def test_start_span(self, adapter):
        """Test starting a span."""
        trace = await adapter.create_trace(
            request_id="req-123",
            app_id="app1",
        )

        span = await adapter.start_span(
            trace_id=trace.trace_id,
            step=TraceStep.POLICY_EVALUATION.value,
            data={"policy_count": 5},
        )

        assert span.step == TraceStep.POLICY_EVALUATION.value
        assert span.started_at is not None
        assert span.ended_at is None
        assert span.data["policy_count"] == 5

        # Trace should be in progress
        updated_trace = await adapter.get_trace(trace.trace_id)
        assert updated_trace.status == TraceStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_end_span(self, adapter):
        """Test ending a span."""
        trace = await adapter.create_trace(
            request_id="req-123",
            app_id="app1",
        )

        await adapter.start_span(
            trace_id=trace.trace_id,
            step=TraceStep.POLICY_EVALUATION.value,
        )

        span = await adapter.end_span(
            trace_id=trace.trace_id,
            step=TraceStep.POLICY_EVALUATION.value,
            status="ok",
            data={"result": "allowed"},
        )

        assert span.ended_at is not None
        assert span.duration_ms is not None
        assert span.status == "ok"
        assert span.data["result"] == "allowed"

    @pytest.mark.asyncio
    async def test_end_span_with_error(self, adapter):
        """Test ending a span with error."""
        trace = await adapter.create_trace(
            request_id="req-123",
            app_id="app1",
        )

        await adapter.start_span(
            trace_id=trace.trace_id,
            step=TraceStep.LLM_REQUEST.value,
        )

        span = await adapter.end_span(
            trace_id=trace.trace_id,
            step=TraceStep.LLM_REQUEST.value,
            status="error",
            error="Connection timeout",
        )

        assert span.status == "error"
        assert span.error == "Connection timeout"

    @pytest.mark.asyncio
    async def test_multiple_spans(self, adapter):
        """Test multiple spans in a trace."""
        trace = await adapter.create_trace(
            request_id="req-123",
            app_id="app1",
        )

        steps = [
            TraceStep.RECEIVED.value,
            TraceStep.POLICY_EVALUATION.value,
            TraceStep.LLM_REQUEST.value,
            TraceStep.COMPLETED.value,
        ]

        for step in steps:
            await adapter.start_span(trace.trace_id, step)
            await adapter.end_span(trace.trace_id, step)

        updated_trace = await adapter.get_trace(trace.trace_id)
        assert len(updated_trace.spans) == 4


class TestTraceCompletion:
    """Tests for trace completion."""

    @pytest.mark.asyncio
    async def test_complete_trace(self, adapter):
        """Test completing a trace successfully."""
        trace = await adapter.create_trace(
            request_id="req-123",
            app_id="app1",
        )

        completed = await adapter.complete_trace(
            trace_id=trace.trace_id,
            outcome="allowed",
            final_data={"tokens_used": 1500},
        )

        assert completed.status == TraceStatus.COMPLETED
        assert completed.outcome == "allowed"
        assert completed.ended_at is not None
        assert completed.total_duration_ms is not None
        assert completed.context["tokens_used"] == 1500

    @pytest.mark.asyncio
    async def test_fail_trace(self, adapter):
        """Test marking a trace as failed."""
        trace = await adapter.create_trace(
            request_id="req-123",
            app_id="app1",
        )

        failed = await adapter.fail_trace(
            trace_id=trace.trace_id,
            error="Policy violation",
            step=TraceStep.POLICY_EVALUATION.value,
        )

        assert failed.status == TraceStatus.FAILED
        assert failed.error == "Policy violation"
        assert failed.context["failed_at_step"] == TraceStep.POLICY_EVALUATION.value

    @pytest.mark.asyncio
    async def test_complete_nonexistent_trace(self, adapter):
        """Test completing a non-existent trace."""
        with pytest.raises(ValueError, match="not found"):
            await adapter.complete_trace("nonexistent", "allowed")


class TestTraceUpdate:
    """Tests for trace updates."""

    @pytest.mark.asyncio
    async def test_update_trace(self, adapter):
        """Test updating trace with data."""
        trace = await adapter.create_trace(
            request_id="req-123",
            app_id="app1",
        )

        updated = await adapter.update_trace(
            trace_id=trace.trace_id,
            step="custom_step",
            data={"key": "value"},
        )

        assert updated.context["custom_step"]["key"] == "value"


class TestTraceQuerying:
    """Tests for trace querying."""

    @pytest.mark.asyncio
    async def test_query_by_app_id(self, adapter):
        """Test querying traces by app ID."""
        for app_id in ["app1", "app2", "app1"]:
            await adapter.create_trace(
                request_id=f"req-{app_id}",
                app_id=app_id,
            )

        filters = TraceFilters(app_id="app1")
        traces = await adapter.query_traces(filters)

        assert len(traces) == 2
        assert all(t.app_id == "app1" for t in traces)

    @pytest.mark.asyncio
    async def test_query_by_status(self, adapter):
        """Test querying traces by status."""
        trace1 = await adapter.create_trace(
            request_id="req-1",
            app_id="app1",
        )
        await adapter.create_trace(
            request_id="req-2",
            app_id="app1",
        )

        await adapter.complete_trace(trace1.trace_id, "allowed")

        filters = TraceFilters(status=TraceStatus.COMPLETED)
        traces = await adapter.query_traces(filters)

        assert len(traces) == 1
        assert traces[0].trace_id == trace1.trace_id

    @pytest.mark.asyncio
    async def test_query_by_outcome(self, adapter):
        """Test querying traces by outcome."""
        trace1 = await adapter.create_trace(request_id="req-1", app_id="app1")
        trace2 = await adapter.create_trace(request_id="req-2", app_id="app1")

        await adapter.complete_trace(trace1.trace_id, "allowed")
        await adapter.complete_trace(trace2.trace_id, "denied")

        filters = TraceFilters(outcome="denied")
        traces = await adapter.query_traces(filters)

        assert len(traces) == 1
        assert traces[0].outcome == "denied"

    @pytest.mark.asyncio
    async def test_query_with_duration_filter(self, adapter):
        """Test querying traces by duration."""
        trace = await adapter.create_trace(
            request_id="req-1",
            app_id="app1",
        )
        await adapter.complete_trace(trace.trace_id, "allowed")

        filters = TraceFilters(min_duration_ms=0)
        traces = await adapter.query_traces(filters)

        assert len(traces) == 1

    @pytest.mark.asyncio
    async def test_query_with_pagination(self, adapter):
        """Test query pagination."""
        for i in range(10):
            await adapter.create_trace(
                request_id=f"req-{i}",
                app_id="app1",
            )

        filters = TraceFilters()

        page1 = await adapter.query_traces(filters, limit=5, offset=0)
        page2 = await adapter.query_traces(filters, limit=5, offset=5)

        assert len(page1) == 5
        assert len(page2) == 5
        assert page1[0].request_id != page2[0].request_id

    @pytest.mark.asyncio
    async def test_get_trace_by_request_id(self, adapter):
        """Test getting trace by request ID."""
        await adapter.create_trace(
            request_id="req-123",
            app_id="app1",
        )

        trace = await adapter.get_trace_by_request_id("req-123")

        assert trace is not None
        assert trace.request_id == "req-123"

    @pytest.mark.asyncio
    async def test_get_trace_by_request_id_not_found(self, adapter):
        """Test getting non-existent request."""
        trace = await adapter.get_trace_by_request_id("nonexistent")

        assert trace is None


class TestAdapterManagement:
    """Tests for adapter management."""

    @pytest.mark.asyncio
    async def test_cleanup_old_traces(self, adapter):
        """Test automatic cleanup of old traces."""
        adapter._max_traces = 5

        # Create more than max traces
        for i in range(10):
            await adapter.create_trace(
                request_id=f"req-{i}",
                app_id="app1",
            )

        assert adapter.get_trace_count() <= 5

    @pytest.mark.asyncio
    async def test_clear(self, adapter):
        """Test clearing all traces."""
        for i in range(5):
            await adapter.create_trace(
                request_id=f"req-{i}",
                app_id="app1",
            )

        assert adapter.get_trace_count() == 5

        adapter.clear()

        assert adapter.get_trace_count() == 0
