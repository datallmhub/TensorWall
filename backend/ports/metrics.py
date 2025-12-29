"""Metrics Port - Interface abstraite pour l'export de métriques.

Architecture Hexagonale: Port (interface) pour les métriques.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class RequestMetrics:
    """Métriques d'une requête LLM."""

    app_id: str
    model: str
    status: str  # success, error, blocked
    latency_seconds: float
    feature: str = "default"
    environment: str = "development"
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


@dataclass
class DecisionMetrics:
    """Métriques d'une décision de gouvernance."""

    app_id: str
    decision: str  # allow, deny, block, warn
    source: str  # policy, budget, security, feature


@dataclass
class BudgetMetrics:
    """Métriques de budget."""

    app_id: str
    feature: str
    environment: str
    usage_ratio: float  # 0.0 - 1.0
    remaining_usd: float


class MetricsPort(ABC):
    """Interface abstraite pour l'export de métriques.

    Cette interface définit le contrat pour enregistrer et exporter
    les métriques du gateway. Les adapters (Prometheus, StatsD, etc.)
    implémentent cette interface.
    """

    @abstractmethod
    def record_request(self, metrics: RequestMetrics) -> None:
        """Enregistre les métriques d'une requête.

        Args:
            metrics: Métriques de la requête (latence, tokens, coût, etc.)
        """
        pass

    @abstractmethod
    def record_decision(self, metrics: DecisionMetrics) -> None:
        """Enregistre une décision de gouvernance.

        Args:
            metrics: Métriques de la décision (allow, deny, source)
        """
        pass

    @abstractmethod
    def record_error(self, app_id: str, error_type: str) -> None:
        """Enregistre une erreur.

        Args:
            app_id: Identifiant de l'application
            error_type: Type d'erreur
        """
        pass

    @abstractmethod
    def record_security_block(self, app_id: str, reason: str) -> None:
        """Enregistre un blocage de sécurité.

        Args:
            app_id: Identifiant de l'application
            reason: Raison du blocage
        """
        pass

    @abstractmethod
    def update_budget(self, metrics: BudgetMetrics) -> None:
        """Met à jour les métriques de budget.

        Args:
            metrics: Métriques de budget (usage, remaining)
        """
        pass

    @abstractmethod
    def request_started(self, app_id: str) -> None:
        """Signale le début d'une requête (pour les requêtes actives).

        Args:
            app_id: Identifiant de l'application
        """
        pass

    @abstractmethod
    def request_finished(self, app_id: str) -> None:
        """Signale la fin d'une requête.

        Args:
            app_id: Identifiant de l'application
        """
        pass

    @abstractmethod
    def export(self) -> str:
        """Exporte les métriques dans le format du backend.

        Returns:
            Chaîne contenant les métriques formatées
        """
        pass
