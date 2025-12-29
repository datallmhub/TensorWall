"""PostgreSQL Adapters - Wrappers autour des repositories legacy.

Architecture Hexagonale: Ces adapters implémentent les Ports de repository
en wrappant le code legacy de backend/services/.
"""

from backend.adapters.postgres.policy_repository_adapter import PolicyRepositoryAdapter
from backend.adapters.postgres.budget_repository_adapter import BudgetRepositoryAdapter


__all__ = [
    "PolicyRepositoryAdapter",
    "BudgetRepositoryAdapter",
]
