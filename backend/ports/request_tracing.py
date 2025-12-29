"""Request Tracing Port - Interface Abstraite.

Architecture Hexagonale: Port pour le traçage des requêtes.

Fonctionnalités:
- Création de traces
- Mise à jour d'étapes
- Requêtage de traces
- Lifecycle complet des requêtes
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class TraceStatus(str, Enum):
    """Statut d'une trace."""

    STARTED = "started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class TraceStep(str, Enum):
    """Étapes possibles d'une trace."""

    RECEIVED = "received"
    ABUSE_CHECK = "abuse_check"
    FEATURE_CHECK = "feature_check"
    POLICY_EVALUATION = "policy_evaluation"
    BUDGET_CHECK = "budget_check"
    LLM_REQUEST = "llm_request"
    LLM_RESPONSE = "llm_response"
    AUDIT_LOG = "audit_log"
    COMPLETED = "completed"


@dataclass
class TraceSpan:
    """Un span dans une trace."""

    step: str
    started_at: datetime
    ended_at: datetime | None = None
    duration_ms: float | None = None
    status: str = "ok"
    data: dict = field(default_factory=dict)
    error: str | None = None


@dataclass
class Trace:
    """Une trace complète."""

    trace_id: str
    request_id: str
    app_id: str
    org_id: str | None
    model: str | None
    status: TraceStatus
    started_at: datetime
    ended_at: datetime | None = None
    total_duration_ms: float | None = None
    outcome: str | None = None
    spans: list[TraceSpan] = field(default_factory=list)
    context: dict = field(default_factory=dict)
    error: str | None = None


@dataclass
class TraceFilters:
    """Filtres pour recherche de traces."""

    app_id: str | None = None
    org_id: str | None = None
    status: TraceStatus | None = None
    outcome: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    min_duration_ms: float | None = None
    max_duration_ms: float | None = None
    has_error: bool | None = None


class RequestTracingPort(ABC):
    """
    Port abstrait pour le traçage des requêtes.

    Permet de suivre le cycle de vie complet d'une requête
    à travers tous les composants du système.
    """

    @abstractmethod
    async def create_trace(
        self,
        request_id: str,
        app_id: str,
        org_id: str | None = None,
        model: str | None = None,
        context: dict | None = None,
    ) -> Trace:
        """
        Crée une nouvelle trace.

        Args:
            request_id: ID de la requête
            app_id: ID de l'application
            org_id: ID de l'organisation
            model: Modèle LLM
            context: Contexte additionnel

        Returns:
            Trace créée
        """
        ...

    @abstractmethod
    async def start_span(
        self,
        trace_id: str,
        step: str,
        data: dict | None = None,
    ) -> TraceSpan:
        """
        Démarre un span dans une trace.

        Args:
            trace_id: ID de la trace
            step: Étape du span
            data: Données associées

        Returns:
            Span démarré
        """
        ...

    @abstractmethod
    async def end_span(
        self,
        trace_id: str,
        step: str,
        status: str = "ok",
        data: dict | None = None,
        error: str | None = None,
    ) -> TraceSpan:
        """
        Termine un span.

        Args:
            trace_id: ID de la trace
            step: Étape du span
            status: Statut final
            data: Données finales
            error: Erreur éventuelle

        Returns:
            Span terminé
        """
        ...

    @abstractmethod
    async def update_trace(
        self,
        trace_id: str,
        step: str,
        data: dict,
    ) -> Trace:
        """
        Met à jour une trace avec des données.

        Args:
            trace_id: ID de la trace
            step: Étape courante
            data: Données à ajouter

        Returns:
            Trace mise à jour
        """
        ...

    @abstractmethod
    async def complete_trace(
        self,
        trace_id: str,
        outcome: str,
        final_data: dict | None = None,
    ) -> Trace:
        """
        Termine une trace avec succès.

        Args:
            trace_id: ID de la trace
            outcome: Résultat (allowed, denied, error)
            final_data: Données finales

        Returns:
            Trace terminée
        """
        ...

    @abstractmethod
    async def fail_trace(
        self,
        trace_id: str,
        error: str,
        step: str | None = None,
        outcome: str | None = None,
    ) -> Trace:
        """
        Marque une trace comme échouée.

        Args:
            trace_id: ID de la trace
            error: Message d'erreur
            step: Étape de l'échec
            outcome: Outcome de la requête (denied_policy, denied_budget, error, etc.)

        Returns:
            Trace échouée
        """
        ...

    @abstractmethod
    async def get_trace(
        self,
        trace_id: str,
    ) -> Trace | None:
        """
        Récupère une trace par ID.

        Args:
            trace_id: ID de la trace

        Returns:
            Trace ou None si non trouvée
        """
        ...

    @abstractmethod
    async def query_traces(
        self,
        filters: TraceFilters,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Trace]:
        """
        Recherche des traces.

        Args:
            filters: Filtres de recherche
            limit: Nombre max de résultats
            offset: Offset pour pagination

        Returns:
            Liste de traces
        """
        ...

    @abstractmethod
    async def get_trace_by_request_id(
        self,
        request_id: str,
    ) -> Trace | None:
        """
        Récupère une trace par request_id.

        Args:
            request_id: ID de la requête

        Returns:
            Trace ou None
        """
        ...
