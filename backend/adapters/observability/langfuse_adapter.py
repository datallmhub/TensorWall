"""
Langfuse Observability Adapter

Sends traces and metrics to Langfuse for LLM observability.

Features:
- Request/response tracing
- Cost tracking
- Latency metrics
- Security findings
- Token usage

Langfuse: https://langfuse.com

Usage:
    from backend.adapters.observability.langfuse_adapter import LangfuseAdapter

    adapter = LangfuseAdapter(
        public_key="pk-...",
        secret_key="sk-...",
    )

    await adapter.trace_request(
        request_id="req_123",
        request=request_data,
        response=response_data,
        metadata=metadata,
    )
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Any
from dataclasses import dataclass
import httpx

logger = logging.getLogger(__name__)


@dataclass
class LangfuseTrace:
    """Represents a Langfuse trace."""
    id: str
    name: str
    input: Optional[dict] = None
    output: Optional[dict] = None
    metadata: Optional[dict] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    tags: Optional[list[str]] = None


@dataclass
class LangfuseGeneration:
    """Represents a Langfuse generation (LLM call)."""
    trace_id: str
    name: str
    model: str
    input: dict
    output: Optional[str] = None
    usage: Optional[dict] = None
    metadata: Optional[dict] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    level: str = "DEFAULT"  # DEFAULT, DEBUG, WARNING, ERROR


class LangfuseAdapter:
    """
    Adapter for sending observability data to Langfuse.

    Implements async batching for performance.
    """

    def __init__(
        self,
        public_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        host: str = "https://cloud.langfuse.com",
        enabled: bool = True,
        batch_size: int = 10,
        flush_interval: float = 5.0,
    ):
        """
        Initialize Langfuse adapter.

        Args:
            public_key: Langfuse public key (or LANGFUSE_PUBLIC_KEY env var)
            secret_key: Langfuse secret key (or LANGFUSE_SECRET_KEY env var)
            host: Langfuse API host
            enabled: Whether to send traces
            batch_size: Number of events to batch before sending
            flush_interval: Seconds between automatic flushes
        """
        import os

        self.public_key = public_key or os.getenv("LANGFUSE_PUBLIC_KEY")
        self.secret_key = secret_key or os.getenv("LANGFUSE_SECRET_KEY")
        self.host = host
        self.enabled = enabled and bool(self.public_key and self.secret_key)
        self.batch_size = batch_size
        self.flush_interval = flush_interval

        self._batch: list[dict] = []
        self._lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None

        if self.enabled:
            logger.info("Langfuse adapter initialized")
        else:
            logger.warning(
                "Langfuse adapter disabled. "
                "Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY to enable."
            )

    async def start(self) -> None:
        """Start the background flush task."""
        if self.enabled and self._flush_task is None:
            self._flush_task = asyncio.create_task(self._flush_loop())

    async def stop(self) -> None:
        """Stop the background flush task and flush remaining events."""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        await self.flush()

    async def _flush_loop(self) -> None:
        """Background loop to flush events periodically."""
        while True:
            await asyncio.sleep(self.flush_interval)
            await self.flush()

    async def flush(self) -> None:
        """Flush all pending events to Langfuse."""
        if not self.enabled or not self._batch:
            return

        async with self._lock:
            events = self._batch.copy()
            self._batch.clear()

        if not events:
            return

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.host}/api/public/ingestion",
                    auth=(self.public_key, self.secret_key),
                    json={"batch": events},
                )

                if response.status_code == 207:
                    # Partial success
                    data = response.json()
                    errors = data.get("errors", [])
                    if errors:
                        logger.warning(f"Langfuse partial errors: {errors}")
                elif response.status_code != 200:
                    logger.error(f"Langfuse flush failed: {response.status_code}")

        except Exception as e:
            logger.error(f"Langfuse flush error: {e}")
            # Put events back in batch for retry
            async with self._lock:
                self._batch = events + self._batch

    async def _add_event(self, event: dict) -> None:
        """Add an event to the batch."""
        if not self.enabled:
            return

        async with self._lock:
            self._batch.append(event)

            if len(self._batch) >= self.batch_size:
                # Trigger immediate flush
                asyncio.create_task(self.flush())

    async def trace_request(
        self,
        request_id: str,
        app_id: str,
        model: str,
        messages: list[dict],
        response_content: Optional[str] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost_usd: float = 0.0,
        latency_ms: int = 0,
        decision: str = "ALLOW",
        security_findings: Optional[list[dict]] = None,
        error: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """
        Trace an LLM request to Langfuse.

        Args:
            request_id: Unique request identifier
            app_id: Application ID
            model: LLM model used
            messages: Input messages
            response_content: LLM response content
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cost_usd: Cost in USD
            latency_ms: Latency in milliseconds
            decision: TensorWall decision (ALLOW, WARN, BLOCK)
            security_findings: Security findings if any
            error: Error message if failed
            metadata: Additional metadata
        """
        now = datetime.utcnow().isoformat() + "Z"

        # Create trace
        trace_event = {
            "type": "trace-create",
            "body": {
                "id": request_id,
                "name": f"tensorwall-{model}",
                "userId": app_id,
                "metadata": {
                    "tensorwall_decision": decision,
                    "tensorwall_security_findings": security_findings or [],
                    "app_id": app_id,
                    **(metadata or {}),
                },
                "tags": [
                    f"model:{model}",
                    f"decision:{decision}",
                    "tensorwall",
                ],
            },
        }
        await self._add_event(trace_event)

        # Create generation (LLM call)
        generation_event = {
            "type": "generation-create",
            "body": {
                "traceId": request_id,
                "name": model,
                "model": model,
                "input": messages,
                "output": response_content,
                "usage": {
                    "input": input_tokens,
                    "output": output_tokens,
                    "total": input_tokens + output_tokens,
                    "inputCost": cost_usd * (input_tokens / (input_tokens + output_tokens + 0.001)),
                    "outputCost": cost_usd * (output_tokens / (input_tokens + output_tokens + 0.001)),
                    "totalCost": cost_usd,
                },
                "metadata": {
                    "latency_ms": latency_ms,
                    "decision": decision,
                },
                "level": "ERROR" if error else "DEFAULT",
                "statusMessage": error,
            },
        }
        await self._add_event(generation_event)

        # Add security span if findings
        if security_findings:
            security_event = {
                "type": "span-create",
                "body": {
                    "traceId": request_id,
                    "name": "security-check",
                    "metadata": {
                        "findings_count": len(security_findings),
                        "findings": security_findings,
                    },
                    "level": "WARNING" if security_findings else "DEFAULT",
                },
            }
            await self._add_event(security_event)

    async def trace_error(
        self,
        request_id: str,
        app_id: str,
        error: str,
        error_code: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """Trace an error to Langfuse."""
        event = {
            "type": "trace-create",
            "body": {
                "id": request_id,
                "name": "tensorwall-error",
                "userId": app_id,
                "metadata": {
                    "error": error,
                    "error_code": error_code,
                    **(metadata or {}),
                },
                "tags": ["error", "tensorwall"],
            },
        }
        await self._add_event(event)


# Default singleton
langfuse_adapter: Optional[LangfuseAdapter] = None


def get_langfuse_adapter() -> Optional[LangfuseAdapter]:
    """Get or create the Langfuse adapter."""
    global langfuse_adapter
    if langfuse_adapter is None:
        langfuse_adapter = LangfuseAdapter()
    return langfuse_adapter if langfuse_adapter.enabled else None
