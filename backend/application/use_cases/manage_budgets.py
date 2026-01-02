"""Manage Budgets Use Case.

Architecture Hexagonale: Use Cases pour la gestion CRUD des budgets.
"""

from dataclasses import dataclass

from backend.domain.models import Budget, BudgetPeriod
from backend.domain.budget import BudgetChecker, BudgetStatus
from backend.ports.budget_repository import BudgetRepositoryPort


@dataclass
class BudgetDTO:
    """DTO pour les budgets."""

    id: str
    app_id: str
    limit_usd: float
    spent_usd: float
    remaining_usd: float
    usage_percent: float
    period: str
    is_exceeded: bool


@dataclass
class CreateBudgetCommand:
    """Command pour créer un budget."""

    app_id: str
    limit_usd: float
    period: str = "monthly"
    org_id: str | None = None


@dataclass
class UpdateBudgetCommand:
    """Command pour mettre à jour un budget."""

    budget_id: str
    limit_usd: float | None = None
    period: str | None = None


@dataclass
class BudgetCheckCommand:
    """Command pour vérifier un budget."""

    app_id: str
    estimated_cost_usd: float
    org_id: str | None = None


class ManageBudgetsUseCase:
    """Use Case: Gérer les budgets (CRUD + check).

    Orchestration pour les opérations sur les budgets.
    """

    def __init__(
        self,
        budget_repository: BudgetRepositoryPort,
        budget_checker: BudgetChecker,
    ):
        self.budget_repository = budget_repository
        self.budget_checker = budget_checker

    def _to_dto(self, budget: Budget) -> BudgetDTO:
        """Convertit un Budget en DTO."""
        return BudgetDTO(
            id=budget.id,
            app_id=budget.app_id,
            limit_usd=budget.limit_usd,
            spent_usd=budget.spent_usd,
            remaining_usd=budget.remaining_usd,
            usage_percent=budget.usage_percent,
            period=budget.period.value if budget.period else "monthly",
            is_exceeded=budget.is_exceeded,
        )

    async def list_budgets(
        self, app_id: str, org_id: str | None = None
    ) -> list[BudgetDTO]:
        """Liste les budgets pour une application."""
        budgets = await self.budget_repository.get_budgets_for_app(
            app_id=app_id,
            org_id=org_id,
        )
        return [self._to_dto(b) for b in budgets]

    async def get_budget(self, budget_id: str) -> BudgetDTO | None:
        """Récupère un budget par ID."""
        budget = await self.budget_repository.get_budget_by_id(budget_id)
        if not budget:
            return None
        return self._to_dto(budget)

    async def create_budget(self, command: CreateBudgetCommand) -> BudgetDTO:
        """Crée un nouveau budget."""
        period = (
            BudgetPeriod(command.period) if command.period else BudgetPeriod.MONTHLY
        )
        budget = Budget(
            id="",  # Sera généré par le repository
            app_id=command.app_id,
            limit_usd=command.limit_usd,
            spent_usd=0.0,
            period=period,
        )
        created = await self.budget_repository.create_budget(budget)
        return self._to_dto(created)

    async def update_budget(self, command: UpdateBudgetCommand) -> BudgetDTO | None:
        """Met à jour un budget."""
        existing = await self.budget_repository.get_budget_by_id(command.budget_id)
        if not existing:
            return None

        if command.limit_usd is not None:
            existing.limit_usd = command.limit_usd
        if command.period is not None:
            existing.period = BudgetPeriod(command.period)

        updated = await self.budget_repository.update_budget(existing)
        return self._to_dto(updated)

    async def check_budget(self, command: BudgetCheckCommand) -> BudgetStatus:
        """Vérifie si un coût estimé respecte les budgets."""
        budgets = await self.budget_repository.get_budgets_for_app(
            app_id=command.app_id,
            org_id=command.org_id,
        )
        return self.budget_checker.check(budgets, command.estimated_cost_usd)

    async def delete_budget(self, budget_id: str) -> bool:
        """Supprime un budget."""
        return await self.budget_repository.delete_budget(budget_id)
