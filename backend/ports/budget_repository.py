"""Budget Repository Port - Interface abstraite pour le stockage des budgets.

Architecture Hexagonale: Port (interface) pour accéder aux budgets.
"""

from abc import ABC, abstractmethod

from backend.domain.models import Budget


class BudgetRepositoryPort(ABC):
    """Interface abstraite pour le repository des budgets.

    Cette interface définit le contrat pour accéder aux budgets.
    Les adapters (PostgreSQL, In-Memory, etc.) implémentent cette interface.
    """

    @abstractmethod
    async def get_budgets_for_app(
        self,
        app_id: str,
        org_id: str | None = None,
    ) -> list[Budget]:
        """Récupère les budgets pour une application.

        Args:
            app_id: Identifiant de l'application
            org_id: Identifiant de l'organisation (optionnel)

        Returns:
            Liste des budgets applicables
        """
        pass

    @abstractmethod
    async def get_budget_by_id(self, budget_id: str) -> Budget | None:
        """Récupère un budget par son ID.

        Args:
            budget_id: Identifiant du budget

        Returns:
            Le budget ou None si non trouvé
        """
        pass

    @abstractmethod
    async def create_budget(self, budget: Budget) -> Budget:
        """Crée un nouveau budget.

        Args:
            budget: Le budget à créer

        Returns:
            Le budget créé avec son ID
        """
        pass

    @abstractmethod
    async def update_budget(self, budget: Budget) -> Budget:
        """Met à jour un budget existant.

        Args:
            budget: Le budget à mettre à jour

        Returns:
            Le budget mis à jour
        """
        pass

    @abstractmethod
    async def record_usage(
        self,
        budget_id: str,
        amount_usd: float,
    ) -> Budget:
        """Enregistre une consommation sur un budget.

        Args:
            budget_id: Identifiant du budget
            amount_usd: Montant consommé en USD

        Returns:
            Le budget mis à jour
        """
        pass

    @abstractmethod
    async def delete_budget(self, budget_id: str) -> bool:
        """Supprime un budget.

        Args:
            budget_id: Identifiant du budget à supprimer

        Returns:
            True si supprimé, False si non trouvé
        """
        pass
