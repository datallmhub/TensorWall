"""Domain Layer - Pure Business Logic.

Ce module contient la logique métier pure, SANS aucune dépendance externe.
Aucun import de SQLAlchemy, Pydantic, FastAPI, etc.

Architecture Hexagonale:
- Le Domain ne dépend de RIEN
- Toutes les dépendances pointent vers le Domain
"""

# Models (Entities & Value Objects)
from backend.domain.models import (
    # Enums
    Environment,
    PolicyAction,
    BudgetPeriod,
    DecisionOutcome,
    # Entities
    PolicyRule,
    Budget,
    GatewayDecision,
    # Chat DTOs
    ChatMessage,
    ChatRequest,
    ChatResponse,
    # Embedding DTOs
    EmbeddingRequest,
    EmbeddingData,
    EmbeddingResponse,
)

# Policy Evaluation
from backend.domain.policy import PolicyDecision, PolicyEvaluator

# Budget Checking
from backend.domain.budget import BudgetStatus, BudgetChecker


__all__ = [
    # Enums
    "Environment",
    "PolicyAction",
    "BudgetPeriod",
    "DecisionOutcome",
    # Entities
    "PolicyRule",
    "Budget",
    "GatewayDecision",
    # Chat DTOs
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    # Embedding DTOs
    "EmbeddingRequest",
    "EmbeddingData",
    "EmbeddingResponse",
    # Policy
    "PolicyDecision",
    "PolicyEvaluator",
    # Budget
    "BudgetStatus",
    "BudgetChecker",
]
