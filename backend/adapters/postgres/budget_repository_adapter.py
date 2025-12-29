"""Budget Repository Adapter - Implémentation native SQLAlchemy.

Architecture Hexagonale: Adapter natif qui implémente directement
l'interface BudgetRepositoryPort en utilisant SQLAlchemy.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ports.budget_repository import BudgetRepositoryPort
from backend.domain.models import Budget as DomainBudget, BudgetPeriod as DomainBudgetPeriod
from backend.db.models import (
    Budget as DBBudget,
    BudgetPeriod as DBBudgetPeriod,
    BudgetScope,
    Application,
)
from backend.db.session import get_db_context


class BudgetRepositoryAdapter(BudgetRepositoryPort):
    """Adapter natif pour le repository des budgets.

    Implémente directement l'interface BudgetRepositoryPort en utilisant
    SQLAlchemy pour les opérations de base de données.
    Aucune dépendance au code legacy (services/).
    """

    def __init__(self, session: AsyncSession | None = None):
        """Initialise l'adapter.

        Args:
            session: Session SQLAlchemy optionnelle. Si non fournie,
                    une nouvelle session sera créée pour chaque opération.
        """
        self._session = session

    def _to_domain(self, db_budget: DBBudget, app_id: str | None = None) -> DomainBudget:
        """Convertit un modèle SQLAlchemy vers le domaine.

        Args:
            db_budget: Modèle SQLAlchemy Budget
            app_id: ID de l'application (optionnel, pour éviter une jointure)

        Returns:
            Entité domain Budget
        """
        # Map DB period to domain period
        period_map = {
            DBBudgetPeriod.HOURLY: DomainBudgetPeriod.HOURLY,
            DBBudgetPeriod.DAILY: DomainBudgetPeriod.DAILY,
            DBBudgetPeriod.WEEKLY: DomainBudgetPeriod.WEEKLY,
            DBBudgetPeriod.MONTHLY: DomainBudgetPeriod.MONTHLY,
        }
        period = period_map.get(db_budget.period, DomainBudgetPeriod.MONTHLY)

        return DomainBudget(
            id=str(db_budget.id),
            app_id=app_id or "",
            limit_usd=db_budget.hard_limit_usd,
            spent_usd=db_budget.current_spend_usd,
            period=period,
        )

    async def get_budgets_for_app(
        self,
        app_id: str,
        org_id: str | None = None,
    ) -> list[DomainBudget]:
        """Récupère les budgets pour une application.

        Args:
            app_id: Identifiant de l'application
            org_id: Identifiant de l'organisation (optionnel)

        Returns:
            Liste des budgets applicables
        """
        async with self._get_session() as session:
            # D'abord trouver l'application
            app_result = await session.execute(
                select(Application).where(Application.app_id == app_id)
            )
            app = app_result.scalar_one_or_none()

            if not app:
                return []

            # Construire la requête de base
            query = select(DBBudget).where(
                DBBudget.is_active.is_(True),
                (
                    (DBBudget.application_id == app.id)
                    | (DBBudget.application_id.is_(None))  # Include global budgets
                ),
            )

            # Filtrer par org_id si fourni
            if org_id:
                query = query.where((DBBudget.org_id == org_id) | (DBBudget.org_id.is_(None)))

            result = await session.execute(query)
            db_budgets = result.scalars().all()

            return [self._to_domain(b, app_id) for b in db_budgets]

    async def get_budget_by_id(self, budget_id: str) -> DomainBudget | None:
        """Récupère un budget par son ID.

        Args:
            budget_id: Identifiant du budget (string représentant un int)

        Returns:
            Le budget ou None si non trouvé
        """
        try:
            bid = int(budget_id)
        except ValueError:
            return None

        async with self._get_session() as session:
            result = await session.execute(select(DBBudget).where(DBBudget.id == bid))
            db_budget = result.scalar_one_or_none()

            if not db_budget:
                return None

            # Récupérer l'app_id si possible
            app_id = ""
            if db_budget.application_id:
                app_result = await session.execute(
                    select(Application).where(Application.id == db_budget.application_id)
                )
                app = app_result.scalar_one_or_none()
                if app:
                    app_id = app.app_id

            return self._to_domain(db_budget, app_id)

    async def create_budget(self, budget: DomainBudget) -> DomainBudget:
        """Crée un nouveau budget.

        Args:
            budget: Le budget à créer

        Returns:
            Le budget créé avec son ID
        """
        async with self._get_session() as session:
            # Trouver l'application
            app_result = await session.execute(
                select(Application).where(Application.app_id == budget.app_id)
            )
            app = app_result.scalar_one_or_none()

            # Map domain period to DB period
            period_map = {
                DomainBudgetPeriod.HOURLY: DBBudgetPeriod.HOURLY,
                DomainBudgetPeriod.DAILY: DBBudgetPeriod.DAILY,
                DomainBudgetPeriod.WEEKLY: DBBudgetPeriod.WEEKLY,
                DomainBudgetPeriod.MONTHLY: DBBudgetPeriod.MONTHLY,
            }
            db_period = period_map.get(budget.period, DBBudgetPeriod.MONTHLY)

            db_budget = DBBudget(
                scope=BudgetScope.APPLICATION,
                application_id=app.id if app else None,
                soft_limit_usd=budget.limit_usd * 0.8,  # 80% pour soft limit
                hard_limit_usd=budget.limit_usd,
                period=db_period,
                current_spend_usd=budget.spent_usd,
            )
            session.add(db_budget)
            await session.flush()
            await session.refresh(db_budget)

            return self._to_domain(db_budget, budget.app_id)

    async def update_budget(self, budget: DomainBudget) -> DomainBudget:
        """Met à jour un budget existant.

        Args:
            budget: Le budget à mettre à jour

        Returns:
            Le budget mis à jour

        Raises:
            ValueError: Si l'ID est invalide ou le budget n'existe pas
        """
        try:
            bid = int(budget.id)
        except ValueError:
            raise ValueError(f"Invalid budget ID: {budget.id}")

        async with self._get_session() as session:
            result = await session.execute(select(DBBudget).where(DBBudget.id == bid))
            db_budget = result.scalar_one_or_none()

            if not db_budget:
                raise ValueError(f"Budget not found: {budget.id}")

            # Map domain period to DB period
            period_map = {
                DomainBudgetPeriod.HOURLY: DBBudgetPeriod.HOURLY,
                DomainBudgetPeriod.DAILY: DBBudgetPeriod.DAILY,
                DomainBudgetPeriod.WEEKLY: DBBudgetPeriod.WEEKLY,
                DomainBudgetPeriod.MONTHLY: DBBudgetPeriod.MONTHLY,
            }
            db_period = period_map.get(budget.period, DBBudgetPeriod.MONTHLY)

            # Mettre à jour les champs
            db_budget.hard_limit_usd = budget.limit_usd
            db_budget.soft_limit_usd = budget.limit_usd * 0.8
            db_budget.current_spend_usd = budget.spent_usd
            db_budget.period = db_period

            await session.flush()
            await session.refresh(db_budget)

            return self._to_domain(db_budget, budget.app_id)

    async def record_usage(
        self,
        budget_id: str,
        amount_usd: float,
    ) -> DomainBudget:
        """Enregistre une consommation sur un budget.

        Args:
            budget_id: Identifiant du budget
            amount_usd: Montant consommé en USD

        Returns:
            Le budget mis à jour

        Raises:
            ValueError: Si l'ID est invalide ou le budget n'existe pas
        """
        try:
            bid = int(budget_id)
        except ValueError:
            raise ValueError(f"Invalid budget ID: {budget_id}")

        async with self._get_session() as session:
            result = await session.execute(select(DBBudget).where(DBBudget.id == bid))
            db_budget = result.scalar_one_or_none()

            if not db_budget:
                raise ValueError(f"Budget not found: {budget_id}")

            # Ajouter la consommation
            db_budget.current_spend_usd += amount_usd

            await session.flush()
            await session.refresh(db_budget)

            # Récupérer l'app_id
            app_id = ""
            if db_budget.application_id:
                app_result = await session.execute(
                    select(Application).where(Application.id == db_budget.application_id)
                )
                app = app_result.scalar_one_or_none()
                if app:
                    app_id = app.app_id

            return self._to_domain(db_budget, app_id)

    async def delete_budget(self, budget_id: str) -> bool:
        """Supprime un budget.

        Args:
            budget_id: Identifiant du budget à supprimer

        Returns:
            True si supprimé, False si non trouvé
        """
        try:
            bid = int(budget_id)
        except ValueError:
            return False

        async with self._get_session() as session:
            result = await session.execute(select(DBBudget).where(DBBudget.id == bid))
            db_budget = result.scalar_one_or_none()

            if not db_budget:
                return False

            await session.delete(db_budget)
            return True

    def _get_session(self):
        """Retourne une session SQLAlchemy (context manager async).

        Si une session a été fournie au constructeur, l'utilise.
        Sinon, crée une nouvelle session via le context manager.
        """
        if self._session:
            return _SessionWrapper(self._session)
        else:
            return get_db_context()


class _SessionWrapper:
    """Wrapper pour utiliser une session existante comme context manager."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
