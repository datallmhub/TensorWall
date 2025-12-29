"""Adapters Layer - Driven Adapters (implementations).

Architecture Hexagonale: Les Adapters implémentent les Ports (interfaces).
Implémentations natives utilisant directement les libs (httpx, SQLAlchemy, redis.asyncio).

Structure:
- llm/        : Adapters pour les providers LLM (OpenAI, Anthropic, etc.)
- postgres/   : Adapters pour les repositories PostgreSQL
- redis/      : Adapters pour le cache Redis
- audit/      : Adapters pour l'audit logging
- prometheus/ : Adapters pour les métriques Prometheus
- abuse/      : Adapters pour la détection d'abus
- feature/    : Adapters pour le registre de features
"""

from backend.adapters.llm import OpenAIAdapter, AnthropicAdapter, MockAdapter
from backend.adapters.postgres import PolicyRepositoryAdapter, BudgetRepositoryAdapter
from backend.adapters.redis import (
    RedisCacheAdapter,
    InMemoryCacheAdapter,
    create_redis_cache_adapter,
)
from backend.adapters.audit import PostgresAuditAdapter, InMemoryAuditAdapter
from backend.adapters.prometheus import PrometheusMetricsAdapter, InMemoryMetricsAdapter
from backend.adapters.abuse import InMemoryAbuseAdapter
from backend.adapters.feature import InMemoryFeatureAdapter


__all__ = [
    # LLM Adapters
    "OpenAIAdapter",
    "AnthropicAdapter",
    "MockAdapter",
    # Repository Adapters
    "PolicyRepositoryAdapter",
    "BudgetRepositoryAdapter",
    # Cache Adapters
    "RedisCacheAdapter",
    "InMemoryCacheAdapter",
    "create_redis_cache_adapter",
    # Audit Adapters
    "PostgresAuditAdapter",
    "InMemoryAuditAdapter",
    # Metrics Adapters
    "PrometheusMetricsAdapter",
    "InMemoryMetricsAdapter",
    # Abuse Adapters
    "InMemoryAbuseAdapter",
    # Feature Adapters
    "InMemoryFeatureAdapter",
]
