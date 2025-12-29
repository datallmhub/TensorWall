"""Observability Port - Interface Abstraite.

Architecture Hexagonale: Port pour l'observabilité enrichie.

Fonctionnalités:
- Analytics de coûts
- Efficacité des tokens
- Détection d'anomalies
- KPIs de gouvernance
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class AnomalyType(str, Enum):
    """Types d'anomalies détectables."""

    COST_SPIKE = "cost_spike"
    TOKEN_SPIKE = "token_spike"
    ERROR_SPIKE = "error_spike"
    LATENCY_SPIKE = "latency_spike"
    UNUSUAL_PATTERN = "unusual_pattern"


class AnomalySeverity(str, Enum):
    """Sévérité des anomalies."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CostFilters:
    """Filtres pour l'analyse de coûts."""

    start_date: datetime | None = None
    end_date: datetime | None = None
    app_id: str | None = None
    org_id: str | None = None
    model: str | None = None
    environment: str | None = None


@dataclass
class CostBreakdown:
    """Répartition des coûts."""

    total_cost_usd: float
    by_model: dict[str, float] = field(default_factory=dict)
    by_app: dict[str, float] = field(default_factory=dict)
    by_environment: dict[str, float] = field(default_factory=dict)
    by_day: dict[str, float] = field(default_factory=dict)
    period_start: datetime | None = None
    period_end: datetime | None = None


@dataclass
class TokenEfficiency:
    """Métriques d'efficacité des tokens."""

    app_id: str
    total_input_tokens: int
    total_output_tokens: int
    avg_input_per_request: float
    avg_output_per_request: float
    input_output_ratio: float
    cost_per_1k_tokens: float


@dataclass
class Anomaly:
    """Anomalie détectée."""

    anomaly_id: str
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    app_id: str | None
    description: str
    detected_at: datetime
    metric_value: float
    expected_value: float
    deviation_percent: float
    metadata: dict = field(default_factory=dict)


@dataclass
class GovernanceKPIs:
    """KPIs de gouvernance."""

    org_id: str
    total_requests: int
    allowed_requests: int
    denied_requests: int
    approval_rate: float
    total_cost_usd: float
    budget_utilization_percent: float
    avg_latency_ms: float
    error_rate: float
    top_models: list[tuple[str, int]] = field(default_factory=list)
    top_apps: list[tuple[str, int]] = field(default_factory=list)


class ObservabilityPort(ABC):
    """
    Port abstrait pour l'observabilité enrichie.

    Étend les fonctionnalités de base de MetricsPort avec
    des analyses avancées et détection d'anomalies.
    """

    @abstractmethod
    async def get_cost_breakdown(
        self,
        filters: CostFilters,
    ) -> CostBreakdown:
        """
        Obtient la répartition des coûts.

        Args:
            filters: Filtres pour l'analyse

        Returns:
            Répartition détaillée des coûts
        """
        ...

    @abstractmethod
    async def get_token_efficiency(
        self,
        app_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> TokenEfficiency:
        """
        Analyse l'efficacité des tokens pour une app.

        Args:
            app_id: ID de l'application
            start_date: Début de la période
            end_date: Fin de la période

        Returns:
            Métriques d'efficacité
        """
        ...

    @abstractmethod
    async def detect_anomalies(
        self,
        app_id: str | None = None,
        lookback_hours: int = 24,
    ) -> list[Anomaly]:
        """
        Détecte les anomalies récentes.

        Args:
            app_id: ID de l'application (None = toutes)
            lookback_hours: Heures à analyser

        Returns:
            Liste des anomalies détectées
        """
        ...

    @abstractmethod
    async def get_governance_kpis(
        self,
        org_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> GovernanceKPIs:
        """
        Obtient les KPIs de gouvernance pour une org.

        Args:
            org_id: ID de l'organisation
            start_date: Début de la période
            end_date: Fin de la période

        Returns:
            KPIs de gouvernance
        """
        ...

    @abstractmethod
    async def get_usage_trends(
        self,
        app_id: str,
        metric: str,
        granularity: str = "hour",
        lookback_hours: int = 24,
    ) -> list[tuple[datetime, float]]:
        """
        Obtient les tendances d'utilisation.

        Args:
            app_id: ID de l'application
            metric: Métrique (requests, cost, tokens, latency)
            granularity: Granularité (minute, hour, day)
            lookback_hours: Heures à analyser

        Returns:
            Liste de (timestamp, valeur)
        """
        ...

    @abstractmethod
    async def record_request(
        self,
        app_id: str,
        org_id: str,
        model: str,
        environment: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        latency_ms: float,
        outcome: str,
        feature: str | None = None,
    ) -> None:
        """
        Enregistre les métriques d'une requête.

        Args:
            app_id: ID de l'application
            org_id: ID de l'organisation
            model: Modèle utilisé
            environment: Environnement
            input_tokens: Tokens d'entrée
            output_tokens: Tokens de sortie
            cost_usd: Coût en USD
            latency_ms: Latence en millisecondes
            outcome: Résultat (allowed, denied, error)
            feature: Feature utilisée
        """
        ...
