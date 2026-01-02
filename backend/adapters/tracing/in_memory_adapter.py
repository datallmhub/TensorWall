"""In-Memory Request Tracing Adapter.

Architecture Hexagonale: Implementation native du RequestTracingPort
pour le tracage des requetes.
"""

import uuid
from datetime import datetime

from backend.ports.request_tracing import (
    RequestTracingPort,
    Trace,
    TraceSpan,
    TraceFilters,
    TraceStatus,
)


class InMemoryRequestTracingAdapter(RequestTracingPort):
    """
    Native implementation of request tracing.

    Stores traces in memory for debugging and development.
    """

    def __init__(self, max_traces: int = 10000):
        self._traces: dict[str, Trace] = {}
        self._by_request_id: dict[str, str] = {}  # request_id -> trace_id
        self._max_traces = max_traces

    async def create_trace(
        self,
        request_id: str,
        app_id: str,
        org_id: str | None = None,
        model: str | None = None,
        context: dict | None = None,
    ) -> Trace:
        """Create a new trace."""
        trace_id = str(uuid.uuid4())

        trace = Trace(
            trace_id=trace_id,
            request_id=request_id,
            app_id=app_id,
            org_id=org_id,
            model=model,
            status=TraceStatus.STARTED,
            started_at=datetime.now(),
            context=context or {},
        )

        self._traces[trace_id] = trace
        self._by_request_id[request_id] = trace_id

        # Cleanup old traces if needed
        self._cleanup_if_needed()

        return trace

    async def start_span(
        self,
        trace_id: str,
        step: str,
        data: dict | None = None,
    ) -> TraceSpan:
        """Start a span in a trace."""
        if trace_id not in self._traces:
            raise ValueError(f"Trace {trace_id} not found")

        trace = self._traces[trace_id]
        trace.status = TraceStatus.IN_PROGRESS

        span = TraceSpan(
            step=step,
            started_at=datetime.now(),
            data=data or {},
        )

        trace.spans.append(span)
        return span

    async def end_span(
        self,
        trace_id: str,
        step: str,
        status: str = "ok",
        data: dict | None = None,
        error: str | None = None,
    ) -> TraceSpan:
        """End a span in a trace."""
        if trace_id not in self._traces:
            raise ValueError(f"Trace {trace_id} not found")

        trace = self._traces[trace_id]

        # Find the span
        span = None
        for s in reversed(trace.spans):
            if s.step == step and s.ended_at is None:
                span = s
                break

        if span is None:
            # Create a completed span if not found
            span = TraceSpan(
                step=step,
                started_at=datetime.now(),
            )
            trace.spans.append(span)

        span.ended_at = datetime.now()
        span.status = status
        span.duration_ms = (span.ended_at - span.started_at).total_seconds() * 1000
        if data:
            span.data.update(data)
        if error:
            span.error = error

        return span

    async def update_trace(
        self,
        trace_id: str,
        step: str,
        data: dict,
    ) -> Trace:
        """Update a trace with data."""
        if trace_id not in self._traces:
            raise ValueError(f"Trace {trace_id} not found")

        trace = self._traces[trace_id]
        trace.context.update({step: data})

        return trace

    async def complete_trace(
        self,
        trace_id: str,
        outcome: str,
        final_data: dict | None = None,
    ) -> Trace:
        """Complete a trace successfully."""
        if trace_id not in self._traces:
            raise ValueError(f"Trace {trace_id} not found")

        trace = self._traces[trace_id]
        trace.status = TraceStatus.COMPLETED
        trace.outcome = outcome
        trace.ended_at = datetime.now()
        trace.total_duration_ms = (
            trace.ended_at - trace.started_at
        ).total_seconds() * 1000

        if final_data:
            trace.context.update(final_data)

        return trace

    async def fail_trace(
        self,
        trace_id: str,
        error: str,
        step: str | None = None,
        outcome: str | None = None,
    ) -> Trace:
        """Mark a trace as failed."""
        if trace_id not in self._traces:
            raise ValueError(f"Trace {trace_id} not found")

        trace = self._traces[trace_id]
        trace.status = TraceStatus.FAILED
        trace.error = error
        trace.outcome = outcome or "error"
        trace.ended_at = datetime.now()
        trace.total_duration_ms = (
            trace.ended_at - trace.started_at
        ).total_seconds() * 1000

        if step:
            trace.context["failed_at_step"] = step

        return trace

    async def get_trace(
        self,
        trace_id: str,
    ) -> Trace | None:
        """Get a trace by ID."""
        return self._traces.get(trace_id)

    async def query_traces(
        self,
        filters: TraceFilters,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Trace]:
        """Query traces with filters."""
        results: list[Trace] = []

        for trace in self._traces.values():
            if not self._matches_filters(trace, filters):
                continue
            results.append(trace)

        # Sort by started_at (most recent first)
        results.sort(key=lambda t: t.started_at, reverse=True)

        return results[offset : offset + limit]

    async def get_trace_by_request_id(
        self,
        request_id: str,
    ) -> Trace | None:
        """Get a trace by request ID."""
        trace_id = self._by_request_id.get(request_id)
        if trace_id:
            return self._traces.get(trace_id)
        return None

    def _matches_filters(self, trace: Trace, filters: TraceFilters) -> bool:
        """Check if trace matches filters."""
        if filters.app_id and trace.app_id != filters.app_id:
            return False
        if filters.org_id and trace.org_id != filters.org_id:
            return False
        if filters.status and trace.status != filters.status:
            return False
        if filters.outcome and trace.outcome != filters.outcome:
            return False
        if filters.start_date and trace.started_at < filters.start_date:
            return False
        if filters.end_date and trace.started_at > filters.end_date:
            return False
        if filters.min_duration_ms is not None:
            if (
                trace.total_duration_ms is None
                or trace.total_duration_ms < filters.min_duration_ms
            ):
                return False
        if filters.max_duration_ms is not None:
            if (
                trace.total_duration_ms is None
                or trace.total_duration_ms > filters.max_duration_ms
            ):
                return False
        if filters.has_error is not None:
            has_error = trace.error is not None
            if filters.has_error != has_error:
                return False

        return True

    def _cleanup_if_needed(self) -> None:
        """Remove old traces if exceeding max."""
        if len(self._traces) > self._max_traces:
            # Sort by started_at and remove oldest
            sorted_traces = sorted(
                self._traces.values(),
                key=lambda t: t.started_at,
            )
            to_remove = len(self._traces) - self._max_traces
            for trace in sorted_traces[:to_remove]:
                del self._traces[trace.trace_id]
                if trace.request_id in self._by_request_id:
                    del self._by_request_id[trace.request_id]

    def clear(self) -> None:
        """Clear all traces."""
        self._traces.clear()
        self._by_request_id.clear()

    def get_trace_count(self) -> int:
        """Get number of traces (for testing)."""
        return len(self._traces)
