"""PostgreSQL Request Tracing Adapter.

Architecture Hexagonale: Implémentation du RequestTracingPort
qui persiste les traces dans la table llm_request_traces.
"""

import uuid
from datetime import datetime

from sqlalchemy import select

from backend.ports.request_tracing import (
    RequestTracingPort,
    Trace,
    TraceSpan,
    TraceFilters,
    TraceStatus,
)
from backend.db.models import (
    LLMRequestTrace,
    TraceDecision,
    TraceStatus as DBTraceStatus,
    Environment,
)
from backend.db.session import get_db_context


class PostgresRequestTracingAdapter(RequestTracingPort):
    """
    PostgreSQL implementation of request tracing.

    Persists all request traces to llm_request_traces table
    for analytics and observability.
    """

    def __init__(self):
        # In-memory cache for active traces
        self._active_traces: dict[str, dict] = {}

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
        now = datetime.utcnow()

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

        # Store in memory for active updates
        self._active_traces[trace_id] = {
            "trace": trace,
            "spans": {},
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_usd": 0.0,
            "decision_reasons": [],
            "risk_categories": [],
            "policies_evaluated": [],
        }

        return trace

    async def start_span(
        self,
        trace_id: str,
        step: str,
        data: dict | None = None,
    ) -> TraceSpan:
        """Start a span in a trace."""
        span = TraceSpan(
            step=step,
            started_at=datetime.utcnow(),
            data=data or {},
        )

        if trace_id in self._active_traces:
            self._active_traces[trace_id]["spans"][step] = span

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
        now = datetime.utcnow()

        if trace_id in self._active_traces:
            spans = self._active_traces[trace_id]["spans"]
            if step in spans:
                span = spans[step]
                span.ended_at = now
                span.status = status
                span.error = error
                if span.started_at:
                    span.duration_ms = (now - span.started_at).total_seconds() * 1000
                if data:
                    span.data.update(data)

                    # Track tokens from LLM response
                    if "input_tokens" in data:
                        self._active_traces[trace_id]["input_tokens"] = data[
                            "input_tokens"
                        ]
                    if "output_tokens" in data:
                        self._active_traces[trace_id]["output_tokens"] = data[
                            "output_tokens"
                        ]

                return span

        return TraceSpan(
            step=step, started_at=now, ended_at=now, status=status, error=error
        )

    async def update_trace(
        self,
        trace_id: str,
        step: str,
        data: dict,
    ) -> Trace:
        """Update a trace with data."""
        if trace_id in self._active_traces:
            trace_data = self._active_traces[trace_id]
            trace_data["trace"].context.update({step: data})
            return trace_data["trace"]

        return Trace(
            trace_id=trace_id,
            request_id="",
            app_id="",
            org_id=None,
            model=None,
            status=TraceStatus.IN_PROGRESS,
            started_at=datetime.utcnow(),
        )

    async def complete_trace(
        self,
        trace_id: str,
        outcome: str,
        final_data: dict | None = None,
    ) -> Trace:
        """Complete a trace and persist to database."""
        now = datetime.utcnow()

        if trace_id not in self._active_traces:
            return Trace(
                trace_id=trace_id,
                request_id="",
                app_id="",
                org_id=None,
                model=None,
                status=TraceStatus.COMPLETED,
                started_at=now,
                ended_at=now,
                outcome=outcome,
            )

        trace_data = self._active_traces[trace_id]
        trace = trace_data["trace"]
        trace.ended_at = now
        trace.status = TraceStatus.COMPLETED
        trace.outcome = outcome
        trace.total_duration_ms = (now - trace.started_at).total_seconds() * 1000

        if final_data:
            trace.context.update(final_data)
            if "input_tokens" in final_data:
                trace_data["input_tokens"] = final_data["input_tokens"]
            if "output_tokens" in final_data:
                trace_data["output_tokens"] = final_data["output_tokens"]

        # Persist to database
        await self._persist_trace(trace_data, outcome)

        # Clean up
        del self._active_traces[trace_id]

        return trace

    async def fail_trace(
        self,
        trace_id: str,
        error: str,
        step: str | None = None,
        outcome: str | None = None,
    ) -> Trace:
        """Mark a trace as failed and persist to database."""
        now = datetime.utcnow()

        # Use provided outcome or default to "error"
        final_outcome = outcome or "error"

        if trace_id not in self._active_traces:
            return Trace(
                trace_id=trace_id,
                request_id="",
                app_id="",
                org_id=None,
                model=None,
                status=TraceStatus.FAILED,
                started_at=now,
                ended_at=now,
                error=error,
            )

        trace_data = self._active_traces[trace_id]
        trace = trace_data["trace"]
        trace.ended_at = now
        trace.status = TraceStatus.FAILED
        trace.outcome = final_outcome
        trace.error = error
        trace.total_duration_ms = (now - trace.started_at).total_seconds() * 1000

        # Persist to database with correct outcome
        await self._persist_trace(
            trace_data, final_outcome, error=error, blocked_by=step
        )

        # Clean up
        del self._active_traces[trace_id]

        return trace

    async def get_trace(
        self,
        trace_id: str,
    ) -> Trace | None:
        """Get a trace by ID."""
        if trace_id in self._active_traces:
            return self._active_traces[trace_id]["trace"]

        async with get_db_context() as db:
            stmt = select(LLMRequestTrace).where(LLMRequestTrace.trace_id == trace_id)
            result = await db.execute(stmt)
            db_trace = result.scalar_one_or_none()

            if db_trace:
                return self._db_trace_to_trace(db_trace)

        return None

    async def query_traces(
        self,
        filters: TraceFilters,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Trace]:
        """Query traces with filters."""
        async with get_db_context() as db:
            stmt = select(LLMRequestTrace)

            if filters.app_id:
                stmt = stmt.where(LLMRequestTrace.app_id == filters.app_id)
            if filters.org_id:
                stmt = stmt.where(LLMRequestTrace.tenant_id == filters.org_id)
            if filters.start_date:
                stmt = stmt.where(LLMRequestTrace.timestamp_start >= filters.start_date)
            if filters.end_date:
                stmt = stmt.where(LLMRequestTrace.timestamp_start <= filters.end_date)

            stmt = stmt.order_by(LLMRequestTrace.timestamp_start.desc())
            stmt = stmt.limit(limit).offset(offset)

            result = await db.execute(stmt)
            db_traces = result.scalars().all()

            return [self._db_trace_to_trace(t) for t in db_traces]

    async def get_trace_by_request_id(
        self,
        request_id: str,
    ) -> Trace | None:
        """Get a trace by request_id."""
        # Check active traces first
        for trace_data in self._active_traces.values():
            if trace_data["trace"].request_id == request_id:
                return trace_data["trace"]

        async with get_db_context() as db:
            stmt = select(LLMRequestTrace).where(
                LLMRequestTrace.request_id == request_id
            )
            result = await db.execute(stmt)
            db_trace = result.scalar_one_or_none()

            if db_trace:
                return self._db_trace_to_trace(db_trace)

        return None

    async def _persist_trace(
        self,
        trace_data: dict,
        outcome: str,
        error: str | None = None,
        blocked_by: str | None = None,
    ) -> None:
        """Persist trace to database."""
        trace = trace_data["trace"]

        # Map outcome to decision
        if outcome == "allowed":
            decision = TraceDecision.ALLOW
            status = DBTraceStatus.SUCCESS
        elif outcome == "warned":
            decision = TraceDecision.WARN
            status = DBTraceStatus.SUCCESS
        elif outcome in (
            "denied_policy",
            "denied_budget",
            "denied_abuse",
            "denied_feature",
            "denied_content",
            "denied_risk",
        ):
            decision = TraceDecision.BLOCK
            status = (
                DBTraceStatus.ERROR
            )  # Status is technical (error), decision captures policy outcome (block)
        elif outcome == "dry_run":
            decision = TraceDecision.ALLOW
            status = DBTraceStatus.SUCCESS
        else:
            decision = TraceDecision.BLOCK
            status = DBTraceStatus.ERROR

        # Determine decision reasons
        decision_reasons = trace_data.get("decision_reasons", [])
        if blocked_by and blocked_by not in decision_reasons:
            decision_reasons.append(blocked_by)

        # Calculate latency
        latency_ms = int(trace.total_duration_ms or 0)

        # Get environment from context
        env_str = trace.context.get("environment", "development")
        try:
            environment = Environment(env_str)
        except ValueError:
            environment = Environment.DEVELOPMENT

        # Calculate cost estimate
        input_tokens = trace_data.get("input_tokens", 0)
        output_tokens = trace_data.get("output_tokens", 0)
        cost_usd = self._estimate_cost(trace.model, input_tokens, output_tokens)

        # Create database record
        db_trace = LLMRequestTrace(
            request_id=trace.request_id,
            trace_id=trace.trace_id,
            tenant_id=trace.org_id,
            app_id=trace.app_id,
            feature=trace.context.get("feature"),
            environment=environment,
            provider=self._get_provider_from_model(trace.model),
            model=trace.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            decision=decision,
            decision_reasons=decision_reasons,
            risk_categories=trace_data.get("risk_categories", []),
            policies_evaluated=trace_data.get("policies_evaluated", []),
            estimated_cost_avoided=cost_usd if decision == TraceDecision.BLOCK else 0.0,
            latency_ms=latency_ms,
            status=status,
            error_message=error,
            timestamp_start=trace.started_at,
            timestamp_end=trace.ended_at,
            extra_metadata=trace.context,
        )

        async with get_db_context() as db:
            db.add(db_trace)
            await db.commit()

    def _db_trace_to_trace(self, db_trace: LLMRequestTrace) -> Trace:
        """Convert database trace to domain trace."""
        if db_trace.status == DBTraceStatus.SUCCESS:
            status = TraceStatus.COMPLETED
        elif db_trace.status == DBTraceStatus.ERROR:
            status = TraceStatus.FAILED
        elif db_trace.status == DBTraceStatus.BLOCKED:
            status = TraceStatus.COMPLETED
        else:
            status = TraceStatus.IN_PROGRESS

        return Trace(
            trace_id=db_trace.trace_id or str(db_trace.id),
            request_id=db_trace.request_id,
            app_id=db_trace.app_id,
            org_id=db_trace.tenant_id,
            model=db_trace.model,
            status=status,
            started_at=db_trace.timestamp_start,
            ended_at=db_trace.timestamp_end,
            total_duration_ms=(
                float(db_trace.latency_ms) if db_trace.latency_ms else None
            ),
            outcome=(
                "allowed" if db_trace.decision == TraceDecision.ALLOW else "blocked"
            ),
            context=db_trace.extra_metadata or {},
            error=db_trace.error_message,
        )

    def _estimate_cost(
        self, model: str | None, input_tokens: int, output_tokens: int
    ) -> float:
        """Estimate cost based on model and tokens."""
        if not model:
            return 0.0

        # Cost per 1K tokens (approximate)
        model_lower = model.lower()

        if "gpt-4" in model_lower:
            input_cost = 0.03
            output_cost = 0.06
        elif "gpt-3.5" in model_lower:
            input_cost = 0.0015
            output_cost = 0.002
        elif "claude" in model_lower:
            input_cost = 0.015
            output_cost = 0.075
        else:
            # Local models (ollama, lmstudio) - no cost
            input_cost = 0.0
            output_cost = 0.0

        return (input_tokens / 1000 * input_cost) + (output_tokens / 1000 * output_cost)

    def _get_provider_from_model(self, model: str | None) -> str | None:
        """Infer provider from model name."""
        if not model:
            return None

        model_lower = model.lower()

        if "gpt" in model_lower or "openai" in model_lower:
            return "openai"
        elif "claude" in model_lower or "anthropic" in model_lower:
            return "anthropic"
        elif (
            "llama" in model_lower or "mistral" in model_lower or "qwen" in model_lower
        ):
            return "ollama"
        elif "phi" in model_lower or "local" in model_lower:
            return "lmstudio"

        return "unknown"
