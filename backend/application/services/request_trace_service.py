"""Request Trace Service - Stub for legacy compatibility.

This module provides request tracing functionality.
"""

from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class RequestTraceService:
    """Service for tracing LLM requests."""

    async def create_trace(
        self,
        request_id: str,
        app_id: str,
        feature: str,
        environment: str,
        model: str,
        messages: List[Dict[str, Any]],
        **kwargs,
    ) -> None:
        """Create a new request trace."""
        logger.debug(f"Trace created: {request_id}")

    async def update_decision(
        self, request_id: str, decision: str, reasons: Optional[List[str]] = None, **kwargs
    ) -> None:
        """Update trace with decision."""
        logger.debug(f"Trace decision updated: {request_id} -> {decision}")

    async def finalize_trace(
        self,
        request_id: str,
        status: str,
        response: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        tokens_input: Optional[int] = None,
        tokens_output: Optional[int] = None,
        cost_usd: Optional[float] = None,
        latency_ms: Optional[float] = None,
        **kwargs,
    ) -> None:
        """Finalize the request trace."""
        logger.debug(f"Trace finalized: {request_id} -> {status}")


# Singleton
request_trace_service = RequestTraceService()
