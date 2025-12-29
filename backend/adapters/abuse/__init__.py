"""Abuse Detection Adapters.

Adapters pour la détection d'abus:
- InMemoryAbuseAdapter: Pour les tests (sans Redis)
- RedisAbuseAdapter: Pour la production (avec Redis)
"""

from backend.adapters.abuse.in_memory_abuse_adapter import InMemoryAbuseAdapter

__all__ = [
    "InMemoryAbuseAdapter",
]
