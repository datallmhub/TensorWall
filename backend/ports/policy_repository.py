"""Policy Repository Port - Interface abstraite pour le stockage des policies.

Architecture Hexagonale: Port (interface) pour accéder aux policies.
"""

from abc import ABC, abstractmethod

from backend.domain.models import PolicyRule


class PolicyRepositoryPort(ABC):
    """Interface abstraite pour le repository des policies.

    Cette interface définit le contrat pour accéder aux règles de policy.
    Les adapters (PostgreSQL, In-Memory, etc.) implémentent cette interface.
    """

    @abstractmethod
    async def get_active_rules(
        self,
        org_id: str | None = None,
        app_id: str | None = None,
        environment: str | None = None,
    ) -> list[PolicyRule]:
        """Récupère les règles actives filtrées.

        Args:
            org_id: Filtrer par organisation
            app_id: Filtrer par application
            environment: Filtrer par environnement

        Returns:
            Liste des règles de policy actives
        """
        pass

    @abstractmethod
    async def get_rule_by_id(self, rule_id: str) -> PolicyRule | None:
        """Récupère une règle par son ID.

        Args:
            rule_id: Identifiant de la règle

        Returns:
            La règle ou None si non trouvée
        """
        pass

    @abstractmethod
    async def create_rule(self, rule: PolicyRule) -> PolicyRule:
        """Crée une nouvelle règle.

        Args:
            rule: La règle à créer

        Returns:
            La règle créée avec son ID
        """
        pass

    @abstractmethod
    async def update_rule(self, rule: PolicyRule) -> PolicyRule:
        """Met à jour une règle existante.

        Args:
            rule: La règle à mettre à jour

        Returns:
            La règle mise à jour
        """
        pass

    @abstractmethod
    async def delete_rule(self, rule_id: str) -> bool:
        """Supprime une règle.

        Args:
            rule_id: Identifiant de la règle à supprimer

        Returns:
            True si supprimée, False si non trouvée
        """
        pass
