"""Policy Repository Adapter - Implémentation native SQLAlchemy.

Architecture Hexagonale: Adapter natif qui implémente directement
l'interface PolicyRepositoryPort en utilisant SQLAlchemy.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ports.policy_repository import PolicyRepositoryPort
from backend.domain.models import PolicyRule as DomainPolicyRule, PolicyAction as DomainPolicyAction
from backend.db.models import PolicyRule as DBPolicyRule, PolicyAction as DBPolicyAction
from backend.db.session import get_db_context


class PolicyRepositoryAdapter(PolicyRepositoryPort):
    """Adapter natif pour le repository des policies.

    Implémente directement l'interface PolicyRepositoryPort en utilisant
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

    def _to_domain(self, db_policy: DBPolicyRule) -> DomainPolicyRule:
        """Convertit un modèle SQLAlchemy vers le domaine.

        Args:
            db_policy: Modèle SQLAlchemy PolicyRule

        Returns:
            Entité domain PolicyRule
        """
        return DomainPolicyRule(
            id=str(db_policy.id),
            name=db_policy.name,
            action=DomainPolicyAction(db_policy.action.value),
            priority=db_policy.priority,
            conditions=db_policy.conditions or {},
            enabled=db_policy.is_enabled,
        )

    def _from_domain(self, rule: DomainPolicyRule) -> dict:
        """Convertit une entité domain vers les valeurs pour SQLAlchemy.

        Args:
            rule: Entité domain PolicyRule

        Returns:
            Dict des valeurs pour créer/mettre à jour le modèle DB
        """
        return {
            "name": rule.name,
            "conditions": rule.conditions,
            "action": DBPolicyAction(rule.action.value),
            "priority": rule.priority,
            "is_enabled": rule.enabled,
        }

    async def get_active_rules(
        self,
        org_id: str | None = None,
        app_id: str | None = None,
        environment: str | None = None,
    ) -> list[DomainPolicyRule]:
        """Récupère les règles actives filtrées.

        Args:
            org_id: Filtrer par organisation (non implémenté)
            app_id: Filtrer par application
            environment: Filtrer par environnement (via conditions)

        Returns:
            Liste des règles de policy actives
        """
        async with self._get_session() as session:
            query = select(DBPolicyRule).where(DBPolicyRule.is_enabled.is_(True))

            # Filtrer par application si fourni
            if app_id:
                # Joindre avec la table applications pour filtrer par app_id
                from backend.db.models import Application

                subquery = select(Application.id).where(Application.app_id == app_id)
                query = query.where(
                    (DBPolicyRule.application_id.in_(subquery))
                    | (DBPolicyRule.application_id.is_(None))  # Include global policies
                )

            # Trier par priorité décroissante
            query = query.order_by(DBPolicyRule.priority.desc())

            result = await session.execute(query)
            db_policies = result.scalars().all()

            # Filtrer par environnement si fourni (dans les conditions)
            domain_rules = []
            for policy in db_policies:
                rule = self._to_domain(policy)

                # Si environment est spécifié, vérifier si la règle s'applique
                if environment:
                    env_conditions = rule.conditions.get("environments", [])
                    if env_conditions and environment not in env_conditions:
                        continue

                domain_rules.append(rule)

            return domain_rules

    async def get_rule_by_id(self, rule_id: str) -> DomainPolicyRule | None:
        """Récupère une règle par son ID.

        Args:
            rule_id: Identifiant de la règle (string représentant un int)

        Returns:
            La règle ou None si non trouvée
        """
        try:
            policy_id = int(rule_id)
        except ValueError:
            return None

        async with self._get_session() as session:
            result = await session.execute(select(DBPolicyRule).where(DBPolicyRule.id == policy_id))
            db_policy = result.scalar_one_or_none()

            if not db_policy:
                return None

            return self._to_domain(db_policy)

    async def create_rule(self, rule: DomainPolicyRule) -> DomainPolicyRule:
        """Crée une nouvelle règle.

        Args:
            rule: La règle à créer

        Returns:
            La règle créée avec son ID
        """
        async with self._get_session() as session:
            values = self._from_domain(rule)
            db_policy = DBPolicyRule(**values)
            session.add(db_policy)
            await session.flush()  # Get the ID
            await session.refresh(db_policy)

            return self._to_domain(db_policy)

    async def update_rule(self, rule: DomainPolicyRule) -> DomainPolicyRule:
        """Met à jour une règle existante.

        Args:
            rule: La règle à mettre à jour

        Returns:
            La règle mise à jour

        Raises:
            ValueError: Si l'ID est invalide ou la règle n'existe pas
        """
        try:
            policy_id = int(rule.id)
        except ValueError:
            raise ValueError(f"Invalid policy ID: {rule.id}")

        async with self._get_session() as session:
            result = await session.execute(select(DBPolicyRule).where(DBPolicyRule.id == policy_id))
            db_policy = result.scalar_one_or_none()

            if not db_policy:
                raise ValueError(f"Policy not found: {rule.id}")

            # Mettre à jour les champs
            db_policy.name = rule.name
            db_policy.conditions = rule.conditions
            db_policy.action = DBPolicyAction(rule.action.value)
            db_policy.priority = rule.priority
            db_policy.is_enabled = rule.enabled

            await session.flush()
            await session.refresh(db_policy)

            return self._to_domain(db_policy)

    async def delete_rule(self, rule_id: str) -> bool:
        """Supprime une règle.

        Args:
            rule_id: Identifiant de la règle à supprimer

        Returns:
            True si supprimée, False si non trouvée
        """
        try:
            policy_id = int(rule_id)
        except ValueError:
            return False

        async with self._get_session() as session:
            result = await session.execute(select(DBPolicyRule).where(DBPolicyRule.id == policy_id))
            db_policy = result.scalar_one_or_none()

            if not db_policy:
                return False

            await session.delete(db_policy)
            return True

    def _get_session(self):
        """Retourne une session SQLAlchemy (context manager async).

        Si une session a été fournie au constructeur, l'utilise.
        Sinon, crée une nouvelle session via le context manager.
        """
        if self._session:
            # Utiliser la session fournie (ne pas la fermer)
            return _SessionWrapper(self._session)
        else:
            # Créer une nouvelle session
            return get_db_context()


class _SessionWrapper:
    """Wrapper pour utiliser une session existante comme context manager."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Ne pas fermer la session fournie
        pass
