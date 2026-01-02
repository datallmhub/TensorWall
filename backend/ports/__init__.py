"""Ports Layer - Abstract Interfaces.

Architecture Hexagonale: Les Ports définissent les interfaces abstraites
que les Adapters implémentent. Le Domain dépend des Ports (inversion de dépendance).

Les Ports sont des ABC (Abstract Base Classes) qui définissent les contrats.
"""

from backend.ports.llm_provider import LLMProviderPort
from backend.ports.embedding_provider import EmbeddingProviderPort
from backend.ports.policy_repository import PolicyRepositoryPort
from backend.ports.budget_repository import BudgetRepositoryPort
from backend.ports.cache import CachePort
from backend.ports.audit_log import AuditLogPort, AuditEntry
from backend.ports.metrics import (
    MetricsPort,
    RequestMetrics,
    DecisionMetrics,
    BudgetMetrics,
)
from backend.ports.abuse_detector import AbuseDetectorPort, AbuseCheckResult, AbuseType
from backend.ports.feature_registry import (
    FeatureRegistryPort,
    FeatureDefinition,
    FeatureCheckResult,
    FeatureAction,
    FeatureDecision,
)
from backend.ports.encryption import (
    EncryptionPort,
    KeyRotationStatus,
)
from backend.ports.request_tracing import (
    RequestTracingPort,
    Trace,
    TraceSpan,
    TraceFilters,
    TraceStatus,
    TraceStep,
)
from backend.ports.model_registry import (
    ModelRegistryPort,
    ModelInfo,
    ModelPricing,
    ModelLimits,
    ModelValidation,
    ProviderType,
    ModelStatus,
    ModelCapability,
)


__all__ = [
    "LLMProviderPort",
    "EmbeddingProviderPort",
    "PolicyRepositoryPort",
    "BudgetRepositoryPort",
    "CachePort",
    "AuditLogPort",
    "AuditEntry",
    "MetricsPort",
    "RequestMetrics",
    "DecisionMetrics",
    "BudgetMetrics",
    "AbuseDetectorPort",
    "AbuseCheckResult",
    "AbuseType",
    "FeatureRegistryPort",
    "FeatureDefinition",
    "FeatureCheckResult",
    "FeatureAction",
    "FeatureDecision",
    "EncryptionPort",
    "KeyRotationStatus",
    "RequestTracingPort",
    "Trace",
    "TraceSpan",
    "TraceFilters",
    "TraceStatus",
    "TraceStep",
    "ModelRegistryPort",
    "ModelInfo",
    "ModelPricing",
    "ModelLimits",
    "ModelValidation",
    "ProviderType",
    "ModelStatus",
    "ModelCapability",
]
