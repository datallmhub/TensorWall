"""Abuse Detector Port - Interface abstraite pour la détection d'abus.

Architecture Hexagonale: Port (interface) que les Adapters implémentent.
Permet de détecter les patterns d'abus comme les boucles, retry storms, etc.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class AbuseType(str, Enum):
    """Types d'abus détectés."""

    LOOP_DETECTED = "loop_detected"
    RETRY_STORM = "retry_storm"
    RATE_SPIKE = "rate_spike"
    COST_SPIKE = "cost_spike"
    DUPLICATE_REQUEST = "duplicate_request"
    SELF_REFERENCE = "self_reference"
    SUSPICIOUS_PATTERN = "suspicious_pattern"


@dataclass
class AbuseCheckResult:
    """Résultat de la vérification d'abus.

    Attributes:
        blocked: True si la requête doit être bloquée
        abuse_type: Type d'abus détecté (si blocked=True)
        reason: Raison du blocage
        cooldown_seconds: Temps de cooldown recommandé
        details: Détails additionnels
    """

    blocked: bool
    abuse_type: AbuseType | None = None
    reason: str | None = None
    cooldown_seconds: int = 0
    details: dict = field(default_factory=dict)


class AbuseDetectorPort(ABC):
    """Interface abstraite pour la détection d'abus.

    Cette interface définit le contrat pour les détecteurs d'abus.
    Les adapters concrets (Redis, InMemory) implémentent cette interface.

    Fonctionnalités:
    - Détection de boucles (requêtes identiques répétées)
    - Détection de retry storms (trop d'erreurs)
    - Détection de rate spikes (augmentation soudaine du trafic)
    - Détection de self-reference (patterns dans le contenu)
    """

    @abstractmethod
    async def check_request(
        self,
        app_id: str,
        feature: str,
        model: str,
        messages: list[dict],
        request_id: str | None = None,
    ) -> AbuseCheckResult:
        """Vérifie si une requête doit être bloquée pour abus.

        Args:
            app_id: Identifiant de l'application
            feature: Feature/use-case
            model: Modèle LLM utilisé
            messages: Liste des messages de la requête
            request_id: Identifiant unique de la requête

        Returns:
            AbuseCheckResult indiquant si la requête est bloquée
        """
        pass

    @abstractmethod
    async def record_error(self, app_id: str) -> AbuseCheckResult:
        """Enregistre une erreur pour la détection de retry storm.

        Args:
            app_id: Identifiant de l'application

        Returns:
            AbuseCheckResult si le seuil d'erreurs est dépassé
        """
        pass

    @abstractmethod
    async def record_cost(self, app_id: str, cost: float) -> AbuseCheckResult:
        """Enregistre un coût pour la détection de cost spike.

        Args:
            app_id: Identifiant de l'application
            cost: Coût de la requête

        Returns:
            AbuseCheckResult si un spike de coût est détecté
        """
        pass

    @abstractmethod
    async def clear_app_data(self, app_id: str) -> None:
        """Efface toutes les données d'une application.

        Args:
            app_id: Identifiant de l'application
        """
        pass
