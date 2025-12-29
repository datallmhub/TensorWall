"""Audit Log Port - Interface abstraite pour l'audit logging.

Architecture Hexagonale: Port (interface) pour l'audit.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class AuditEntry:
    """Entrée d'audit."""

    event_type: str
    request_id: str
    app_id: str
    org_id: str | None = None
    user_id: str | None = None
    model: str | None = None
    action: str | None = None
    outcome: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    duration_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


class AuditLogPort(ABC):
    """Interface abstraite pour l'audit logging.

    Cette interface définit le contrat pour enregistrer les événements d'audit.
    Les adapters (PostgreSQL, Elasticsearch, etc.) implémentent cette interface.
    """

    @abstractmethod
    async def log(self, entry: AuditEntry) -> None:
        """Enregistre une entrée d'audit.

        Args:
            entry: L'entrée d'audit à enregistrer
        """
        pass

    @abstractmethod
    async def log_request(
        self,
        request_id: str,
        app_id: str,
        model: str,
        outcome: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Enregistre une requête LLM.

        Args:
            request_id: Identifiant de la requête
            app_id: Identifiant de l'application
            model: Modèle utilisé
            outcome: Résultat (allowed, denied, etc.)
            details: Détails supplémentaires
        """
        pass

    @abstractmethod
    async def log_policy_decision(
        self,
        request_id: str,
        app_id: str,
        policy_id: str,
        action: str,
        reason: str,
    ) -> None:
        """Enregistre une décision de policy.

        Args:
            request_id: Identifiant de la requête
            app_id: Identifiant de l'application
            policy_id: Identifiant de la policy
            action: Action prise (allow, warn, deny)
            reason: Raison de la décision
        """
        pass

    @abstractmethod
    async def get_entries(
        self,
        app_id: str | None = None,
        org_id: str | None = None,
        event_type: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """Récupère les entrées d'audit filtrées.

        Args:
            app_id: Filtrer par application
            org_id: Filtrer par organisation
            event_type: Filtrer par type d'événement
            start_time: Date de début
            end_time: Date de fin
            limit: Nombre maximum d'entrées

        Returns:
            Liste des entrées d'audit
        """
        pass
