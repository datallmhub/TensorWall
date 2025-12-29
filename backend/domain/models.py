"""Domain Models - Pure Python, AUCUNE dépendance externe.

Ce module contient les entités métier pures.
INTERDIT: SQLAlchemy, Pydantic, imports de backend.*
AUTORISÉ: dataclasses, enum, typing, uuid, datetime
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


# =============================================================================
# Enums
# =============================================================================


class Environment(str, Enum):
    """Environnements d'exécution."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class PolicyAction(str, Enum):
    """Actions possibles d'une policy."""

    ALLOW = "allow"
    WARN = "warn"
    DENY = "deny"


class BudgetPeriod(str, Enum):
    """Périodes de budget."""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class DecisionOutcome(str, Enum):
    """Résultat d'une décision."""

    ALLOW = "allow"
    DENY = "deny"
    WARN = "warn"


# =============================================================================
# Domain Entities
# =============================================================================


@dataclass
class PolicyRule:
    """Règle de policy."""

    id: str
    name: str
    action: PolicyAction
    priority: int = 0
    conditions: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


@dataclass
class Budget:
    """Budget pour une application."""

    id: str
    app_id: str
    limit_usd: float
    spent_usd: float = 0.0
    period: BudgetPeriod = BudgetPeriod.MONTHLY

    @property
    def remaining_usd(self) -> float:
        return max(0.0, self.limit_usd - self.spent_usd)

    @property
    def usage_percent(self) -> float:
        if self.limit_usd <= 0:
            return 0.0
        return min(100.0, (self.spent_usd / self.limit_usd) * 100)

    @property
    def is_exceeded(self) -> bool:
        return self.spent_usd >= self.limit_usd


@dataclass
class GatewayDecision:
    """Décision du gateway."""

    outcome: DecisionOutcome
    reason: str
    decision_id: str = field(default_factory=lambda: str(uuid4()))
    details: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_allowed(self) -> bool:
        return self.outcome == DecisionOutcome.ALLOW

    @property
    def is_denied(self) -> bool:
        return self.outcome == DecisionOutcome.DENY


# =============================================================================
# LLM DTOs (pour le domain, pas pour l'API)
# =============================================================================


@dataclass
class ChatMessage:
    """Message de chat."""

    role: str
    content: str


@dataclass
class ChatRequest:
    """Requête de chat."""

    model: str
    messages: list[ChatMessage]
    max_tokens: int | None = None
    temperature: float | None = None
    stream: bool = False


@dataclass
class ChatResponse:
    """Réponse de chat."""

    id: str
    model: str
    content: str
    input_tokens: int
    output_tokens: int
    finish_reason: str | None = None


# =============================================================================
# Embedding DTOs
# =============================================================================


@dataclass
class EmbeddingRequest:
    """Requête d'embedding."""

    model: str
    input: list[str]
    encoding_format: str = "float"


@dataclass
class EmbeddingData:
    """Données d'embedding pour un input."""

    index: int
    embedding: list[float]


@dataclass
class EmbeddingResponse:
    """Réponse d'embedding."""

    model: str
    data: list[EmbeddingData]
    total_tokens: int
