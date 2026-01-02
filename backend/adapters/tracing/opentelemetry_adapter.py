"""OpenTelemetry Request Tracing Adapter.

Architecture Hexagonale: Implémentation production du RequestTracingPort
utilisant OpenTelemetry pour le traçage distribué.

Ce module fournit:
- Traces OpenTelemetry standards
- Export vers Jaeger, Zipkin, OTLP
- Spans avec attributs sémantiques
- Propagation de contexte
"""

import uuid
from datetime import datetime
from typing import Any

from backend.ports.request_tracing import (
    RequestTracingPort,
    Trace,
    TraceSpan,
    TraceFilters,
    TraceStatus,
)


class OpenTelemetryTracingAdapter(RequestTracingPort):
    """
    OpenTelemetry-based request tracing implementation.

    Integrates with OpenTelemetry SDK for distributed tracing.
    Falls back to in-memory storage when OTEL is not available.
    """

    def __init__(
        self,
        service_name: str = "tensorwall",
        otlp_endpoint: str | None = None,
        jaeger_endpoint: str | None = None,
        enable_console_export: bool = False,
    ):
        """
        Initialize OpenTelemetry adapter.

        Args:
            service_name: Service name for traces
            otlp_endpoint: OTLP exporter endpoint
            jaeger_endpoint: Jaeger exporter endpoint
            enable_console_export: Enable console span exporter (for debugging)
        """
        self._service_name = service_name
        self._otlp_endpoint = otlp_endpoint
        self._jaeger_endpoint = jaeger_endpoint

        # In-memory storage
        self._traces: dict[str, Trace] = {}
        self._spans: dict[str, dict[str, TraceSpan]] = {}  # trace_id -> {step: span}

        # OpenTelemetry tracer
        self._tracer = None
        self._otel_spans: dict[str, Any] = {}  # trace_id:step -> otel span
        self._init_opentelemetry(enable_console_export)

    def _init_opentelemetry(self, console_export: bool) -> None:
        """Initialize OpenTelemetry if available."""
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.resources import Resource

            # Create resource
            resource = Resource.create(
                {
                    "service.name": self._service_name,
                    "service.version": "1.0.0",
                }
            )

            # Create provider
            provider = TracerProvider(resource=resource)

            # Add exporters
            if self._otlp_endpoint:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                    OTLPSpanExporter,
                )
                from opentelemetry.sdk.trace.export import BatchSpanProcessor

                otlp_exporter = OTLPSpanExporter(endpoint=self._otlp_endpoint)
                provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

            if self._jaeger_endpoint:
                from opentelemetry.exporter.jaeger.thrift import JaegerExporter
                from opentelemetry.sdk.trace.export import BatchSpanProcessor

                jaeger_exporter = JaegerExporter(
                    agent_host_name=self._jaeger_endpoint.split(":")[0],
                    agent_port=(
                        int(self._jaeger_endpoint.split(":")[1])
                        if ":" in self._jaeger_endpoint
                        else 6831
                    ),
                )
                provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))

            if console_export:
                from opentelemetry.sdk.trace.export import (
                    ConsoleSpanExporter,
                    SimpleSpanProcessor,
                )

                provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

            # Set global provider
            trace.set_tracer_provider(provider)

            # Get tracer
            self._tracer = trace.get_tracer(self._service_name)

        except ImportError:
            # OpenTelemetry not available
            pass

    async def create_trace(
        self,
        request_id: str,
        app_id: str,
        org_id: str | None = None,
        model: str | None = None,
        context: dict | None = None,
    ) -> Trace:
        """Create a new trace."""
        trace_id = f"trace_{uuid.uuid4().hex[:16]}"
        now = datetime.now()

        trace = Trace(
            trace_id=trace_id,
            request_id=request_id,
            app_id=app_id,
            org_id=org_id,
            model=model,
            status=TraceStatus.STARTED,
            started_at=now,
            context=context or {},
        )

        self._traces[trace_id] = trace
        self._spans[trace_id] = {}

        # Start OpenTelemetry span if available
        if self._tracer:
            from opentelemetry.trace import SpanKind

            otel_span = self._tracer.start_span(
                "llm_request",
                kind=SpanKind.SERVER,
            )
            otel_span.set_attribute("request.id", request_id)
            otel_span.set_attribute("app.id", app_id)
            if org_id:
                otel_span.set_attribute("org.id", org_id)
            if model:
                otel_span.set_attribute("llm.model", model)

            self._otel_spans[f"{trace_id}:root"] = otel_span

        return trace

    async def start_span(
        self,
        trace_id: str,
        step: str,
        data: dict | None = None,
    ) -> TraceSpan:
        """Start a span within a trace."""
        if trace_id not in self._traces:
            raise ValueError(f"Trace {trace_id} not found")

        now = datetime.now()
        span = TraceSpan(
            step=step,
            started_at=now,
            data=data or {},
        )

        self._spans[trace_id][step] = span

        # Update trace status
        trace = self._traces[trace_id]
        trace.status = TraceStatus.IN_PROGRESS

        # Start OpenTelemetry span if available
        if self._tracer:
            parent_key = f"{trace_id}:root"
            if parent_key in self._otel_spans:
                from opentelemetry import context as otel_context
                from opentelemetry.trace import set_span_in_context

                parent_span = self._otel_spans[parent_key]
                ctx = set_span_in_context(parent_span)

                with otel_context.attach(ctx):
                    otel_span = self._tracer.start_span(step)
                    if data:
                        for key, value in data.items():
                            if isinstance(value, (str, int, float, bool)):
                                otel_span.set_attribute(f"data.{key}", value)

                    self._otel_spans[f"{trace_id}:{step}"] = otel_span

        return span

    async def end_span(
        self,
        trace_id: str,
        step: str,
        status: str = "ok",
        data: dict | None = None,
        error: str | None = None,
    ) -> TraceSpan:
        """End a span."""
        if trace_id not in self._traces:
            raise ValueError(f"Trace {trace_id} not found")

        if step not in self._spans.get(trace_id, {}):
            raise ValueError(f"Span {step} not found in trace {trace_id}")

        span = self._spans[trace_id][step]
        span.ended_at = datetime.now()
        span.duration_ms = (span.ended_at - span.started_at).total_seconds() * 1000
        span.status = status
        span.error = error
        if data:
            span.data.update(data)

        # End OpenTelemetry span if available
        otel_key = f"{trace_id}:{step}"
        if otel_key in self._otel_spans:
            otel_span = self._otel_spans[otel_key]
            if error:
                from opentelemetry.trace import StatusCode

                otel_span.set_status(StatusCode.ERROR, error)
            if data:
                for key, value in data.items():
                    if isinstance(value, (str, int, float, bool)):
                        otel_span.set_attribute(f"data.{key}", value)
            otel_span.set_attribute("duration_ms", span.duration_ms)
            otel_span.end()

        return span

    async def update_trace(
        self,
        trace_id: str,
        step: str,
        data: dict,
    ) -> Trace:
        """Update trace with additional data."""
        if trace_id not in self._traces:
            raise ValueError(f"Trace {trace_id} not found")

        trace = self._traces[trace_id]
        trace.context[step] = data

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
        trace.ended_at = datetime.now()
        trace.total_duration_ms = (
            trace.ended_at - trace.started_at
        ).total_seconds() * 1000
        trace.status = TraceStatus.COMPLETED
        trace.outcome = outcome
        if final_data:
            trace.context.update(final_data)

        # Add all spans to trace
        trace.spans = list(self._spans.get(trace_id, {}).values())

        # End root OpenTelemetry span
        root_key = f"{trace_id}:root"
        if root_key in self._otel_spans:
            otel_span = self._otel_spans[root_key]
            otel_span.set_attribute("outcome", outcome)
            otel_span.set_attribute("duration_ms", trace.total_duration_ms)
            otel_span.end()

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
        trace.ended_at = datetime.now()
        trace.total_duration_ms = (
            trace.ended_at - trace.started_at
        ).total_seconds() * 1000
        trace.status = TraceStatus.FAILED
        trace.error = error
        trace.outcome = outcome or "error"
        if step:
            trace.context["failed_step"] = step

        # Add all spans to trace
        trace.spans = list(self._spans.get(trace_id, {}).values())

        # End root OpenTelemetry span with error
        root_key = f"{trace_id}:root"
        if root_key in self._otel_spans:
            from opentelemetry.trace import StatusCode

            otel_span = self._otel_spans[root_key]
            otel_span.set_status(StatusCode.ERROR, error)
            otel_span.set_attribute("error.message", error)
            if step:
                otel_span.set_attribute("error.step", step)
            otel_span.end()

        return trace

    async def get_trace(
        self,
        trace_id: str,
    ) -> Trace | None:
        """Get a trace by ID."""
        trace = self._traces.get(trace_id)
        if trace and trace_id in self._spans:
            trace.spans = list(self._spans[trace_id].values())
        return trace

    async def query_traces(
        self,
        filters: TraceFilters,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Trace]:
        """Query traces with filters."""
        results = list(self._traces.values())

        # Apply filters
        if filters.app_id:
            results = [t for t in results if t.app_id == filters.app_id]
        if filters.org_id:
            results = [t for t in results if t.org_id == filters.org_id]
        if filters.status:
            results = [t for t in results if t.status == filters.status]
        if filters.outcome:
            results = [t for t in results if t.outcome == filters.outcome]
        if filters.start_date:
            results = [t for t in results if t.started_at >= filters.start_date]
        if filters.end_date:
            results = [t for t in results if t.started_at <= filters.end_date]
        if filters.min_duration_ms is not None:
            results = [
                t
                for t in results
                if (t.total_duration_ms or 0) >= filters.min_duration_ms
            ]
        if filters.max_duration_ms is not None:
            results = [
                t
                for t in results
                if (t.total_duration_ms or 0) <= filters.max_duration_ms
            ]
        if filters.has_error is not None:
            if filters.has_error:
                results = [t for t in results if t.error is not None]
            else:
                results = [t for t in results if t.error is None]

        # Sort by start time descending
        results.sort(key=lambda t: t.started_at, reverse=True)

        # Add spans to each trace
        for trace in results:
            if trace.trace_id in self._spans:
                trace.spans = list(self._spans[trace.trace_id].values())

        return results[offset : offset + limit]

    async def get_trace_by_request_id(
        self,
        request_id: str,
    ) -> Trace | None:
        """Get a trace by request ID."""
        for trace in self._traces.values():
            if trace.request_id == request_id:
                if trace.trace_id in self._spans:
                    trace.spans = list(self._spans[trace.trace_id].values())
                return trace
        return None

    def clear(self) -> None:
        """Clear all stored data (for testing)."""
        self._traces.clear()
        self._spans.clear()
        self._otel_spans.clear()
