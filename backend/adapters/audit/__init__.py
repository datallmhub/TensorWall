"""Audit Adapters - Implémentations natives.

Architecture Hexagonale: Ces adapters implémentent le Port AuditLogPort
en utilisant directement SQLAlchemy ou des structures en mémoire.
"""

from backend.adapters.audit.postgres_audit_adapter import (
    PostgresAuditAdapter,
    InMemoryAuditAdapter,
)


__all__ = [
    "PostgresAuditAdapter",
    "InMemoryAuditAdapter",
]
