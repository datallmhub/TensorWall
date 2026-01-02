"""Model Registry Adapters.

Architecture Hexagonale: Implementations du ModelRegistryPort.
"""

from backend.adapters.model_registry.in_memory_adapter import (
    InMemoryModelRegistryAdapter,
)
from backend.adapters.model_registry.postgres_adapter import (
    PostgresModelRegistryAdapter,
)

__all__ = [
    "InMemoryModelRegistryAdapter",
    "PostgresModelRegistryAdapter",
]
