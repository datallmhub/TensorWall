from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime
from enum import Enum
import json
import logging

from backend.core.contracts import UsageContract
from backend.application.engines.policy import PolicyDecision


class AuditEventType(str, Enum):
    REQUEST = "request"
    RESPONSE = "response"
    POLICY_DECISION = "policy_decision"
    BUDGET_CHECK = "budget_check"
    SECURITY_CHECK = "security_check"
    ERROR = "error"


class AuditEvent(BaseModel):
    """Événement d'audit."""

    timestamp: datetime = datetime.now()
    event_type: AuditEventType
    request_id: Optional[str] = None

    # Context
    app_id: Optional[str] = None
    feature: Optional[str] = None
    environment: Optional[str] = None
    owner: Optional[str] = None

    # Request details
    model: Optional[str] = None
    provider: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    latency_ms: Optional[int] = None

    # Decisions
    policy_decision: Optional[PolicyDecision] = None
    policy_reason: Optional[str] = None
    budget_allowed: Optional[bool] = None
    cost_usd: Optional[float] = None

    # Security
    security_issues: list[str] = []
    blocked: bool = False

    # Error
    error: Optional[str] = None

    # Extra metadata
    metadata: dict[str, Any] = {}


class AuditLogger:
    """
    Logger d'audit.
    Logs all gateway events for compliance and debugging.
    """

    def __init__(self):
        self.logger = logging.getLogger("llm_gateway.audit")
        self.logger.setLevel(logging.INFO)

        # Console handler for now (TODO: add file/DB handlers)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(asctime)s [AUDIT] %(message)s"))
            self.logger.addHandler(handler)

        # In-memory storage for demo (TODO: move to DB)
        self.events: list[AuditEvent] = []

    def log(self, event: AuditEvent) -> None:
        """Log an audit event."""
        self.events.append(event)

        # Structured log
        log_data = {
            "type": event.event_type.value,
            "app_id": event.app_id,
            "model": event.model,
            "decision": event.policy_decision.value if event.policy_decision else None,
            "blocked": event.blocked,
            "latency_ms": event.latency_ms,
        }

        if event.error:
            self.logger.error(json.dumps(log_data))
        elif event.blocked:
            self.logger.warning(json.dumps(log_data))
        else:
            self.logger.info(json.dumps(log_data))

    def log_request(
        self,
        contract: UsageContract,
        model: str,
        policy_decision: PolicyDecision,
        policy_reason: Optional[str] = None,
        budget_allowed: bool = True,
        security_issues: list[str] = None,
        blocked: bool = False,
    ) -> None:
        """Log a request event."""
        self.log(
            AuditEvent(
                event_type=AuditEventType.REQUEST,
                request_id=contract.request_id,
                app_id=contract.app_id,
                feature=contract.feature,
                environment=contract.environment.value,
                owner=contract.owner,
                model=model,
                policy_decision=policy_decision,
                policy_reason=policy_reason,
                budget_allowed=budget_allowed,
                security_issues=security_issues or [],
                blocked=blocked,
            )
        )

    def log_response(
        self,
        contract: UsageContract,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        cost_usd: float,
        error: Optional[str] = None,
    ) -> None:
        """Log a response event."""
        self.log(
            AuditEvent(
                event_type=AuditEventType.RESPONSE,
                request_id=contract.request_id,
                app_id=contract.app_id,
                feature=contract.feature,
                environment=contract.environment.value,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                cost_usd=cost_usd,
                error=error,
            )
        )

    def get_events(
        self,
        app_id: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """Query audit events."""
        events = self.events

        if app_id:
            events = [e for e in events if e.app_id == app_id]
        if event_type:
            events = [e for e in events if e.event_type == event_type]

        return events[-limit:]


# Singleton
audit_logger = AuditLogger()
