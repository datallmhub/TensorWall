"""Audit Adapters - Implémentations natives.

Architecture Hexagonale: Adapters natifs qui implémentent directement
l'interface AuditLogPort en utilisant SQLAlchemy ou en mémoire.
"""

from datetime import datetime
from typing import Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ports.audit_log import AuditLogPort, AuditEntry
from backend.db.models import AuditLog as DBAuditLog, AuditEventType as DBAuditEventType
from backend.db.session import get_db_context


class PostgresAuditAdapter(AuditLogPort):
    """Adapter natif pour l'audit log en PostgreSQL.

    Implémente directement l'interface AuditLogPort en utilisant
    SQLAlchemy pour les opérations de base de données.
    Aucune dépendance au code legacy (audit/).
    """

    def __init__(self, session: AsyncSession | None = None):
        """Initialise l'adapter.

        Args:
            session: Session SQLAlchemy optionnelle. Si non fournie,
                    une nouvelle session sera créée pour chaque opération.
        """
        self._session = session

    def _to_db(self, entry: AuditEntry) -> dict[str, Any]:
        """Convertit une AuditEntry vers les valeurs pour SQLAlchemy.

        Args:
            entry: Entrée d'audit du domaine

        Returns:
            Dict des valeurs pour créer le modèle DB
        """
        # Map event_type to DB enum
        event_type_map = {
            "llm_request": DBAuditEventType.REQUEST,
            "request": DBAuditEventType.REQUEST,
            "response": DBAuditEventType.RESPONSE,
            "policy_decision": DBAuditEventType.POLICY_DECISION,
            "budget_check": DBAuditEventType.BUDGET_CHECK,
            "security_check": DBAuditEventType.SECURITY_CHECK,
            "error": DBAuditEventType.ERROR,
        }
        db_event_type = event_type_map.get(entry.event_type, DBAuditEventType.REQUEST)

        return {
            "event_type": db_event_type,
            "request_id": entry.request_id,
            "app_id": entry.app_id,
            "owner": entry.user_id,
            "model": entry.model,
            "policy_decision": entry.action,
            "policy_reason": entry.details.get("policy_reasons", []),
            "blocked": entry.outcome in ("denied_policy", "denied_budget", "blocked"),
            "extra_data": {
                "org_id": entry.org_id,
                "outcome": entry.outcome,
                "duration_ms": entry.duration_ms,
                "input_tokens": entry.input_tokens,
                "output_tokens": entry.output_tokens,
                "cost_usd": entry.cost_usd,
                **entry.details,
            },
            "timestamp": entry.timestamp,
        }

    def _from_db(self, db_audit: DBAuditLog) -> AuditEntry:
        """Convertit un modèle SQLAlchemy vers le domaine.

        Args:
            db_audit: Modèle SQLAlchemy AuditLog

        Returns:
            Entité domain AuditEntry
        """
        extra_data = db_audit.extra_data or {}

        return AuditEntry(
            event_type=db_audit.event_type.value,
            request_id=db_audit.request_id or "",
            app_id=db_audit.app_id or "",
            org_id=extra_data.get("org_id"),
            user_id=db_audit.owner,
            model=db_audit.model,
            action=db_audit.policy_decision,
            outcome=extra_data.get("outcome"),
            details={
                "environment": db_audit.environment,
                "feature": db_audit.feature,
                "policy_reason": db_audit.policy_reason,
                "security_issues": db_audit.security_issues,
                "error": db_audit.error,
            },
            timestamp=db_audit.timestamp,
            duration_ms=extra_data.get("duration_ms"),
            input_tokens=extra_data.get("input_tokens"),
            output_tokens=extra_data.get("output_tokens"),
            cost_usd=extra_data.get("cost_usd"),
        )

    async def log(self, entry: AuditEntry) -> None:
        """Enregistre une entrée d'audit.

        Args:
            entry: L'entrée d'audit à enregistrer
        """
        async with self._get_session() as session:
            values = self._to_db(entry)
            db_audit = DBAuditLog(**values)
            session.add(db_audit)
            await session.flush()

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
        entry = AuditEntry(
            event_type="request",
            request_id=request_id,
            app_id=app_id,
            model=model,
            outcome=outcome,
            details=details or {},
        )
        await self.log(entry)

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
        entry = AuditEntry(
            event_type="policy_decision",
            request_id=request_id,
            app_id=app_id,
            action=action,
            details={
                "policy_id": policy_id,
                "reason": reason,
            },
        )
        await self.log(entry)

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
            org_id: Filtrer par organisation (dans extra_data)
            event_type: Filtrer par type d'événement
            start_time: Date de début
            end_time: Date de fin
            limit: Nombre maximum d'entrées

        Returns:
            Liste des entrées d'audit
        """
        async with self._get_session() as session:
            query = select(DBAuditLog)

            # Build filters
            filters = []

            if app_id:
                filters.append(DBAuditLog.app_id == app_id)

            if event_type:
                event_type_map = {
                    "request": DBAuditEventType.REQUEST,
                    "response": DBAuditEventType.RESPONSE,
                    "policy_decision": DBAuditEventType.POLICY_DECISION,
                    "budget_check": DBAuditEventType.BUDGET_CHECK,
                    "security_check": DBAuditEventType.SECURITY_CHECK,
                    "error": DBAuditEventType.ERROR,
                }
                if event_type in event_type_map:
                    filters.append(DBAuditLog.event_type == event_type_map[event_type])

            if start_time:
                filters.append(DBAuditLog.timestamp >= start_time)

            if end_time:
                filters.append(DBAuditLog.timestamp <= end_time)

            if filters:
                query = query.where(and_(*filters))

            # Order and limit
            query = query.order_by(DBAuditLog.timestamp.desc()).limit(limit)

            result = await session.execute(query)
            db_entries = result.scalars().all()

            entries = [self._from_db(entry) for entry in db_entries]

            # Filter by org_id if specified (stored in extra_data)
            if org_id:
                entries = [e for e in entries if e.org_id == org_id]

            return entries

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
        # Ne pas fermer la session fournie
        pass


class InMemoryAuditAdapter(AuditLogPort):
    """Adapter en mémoire pour l'audit log (pour les tests).

    Stocke les entrées d'audit en mémoire sans persistance.
    Utile pour les tests unitaires et d'intégration.
    """

    def __init__(self):
        """Initialise l'adapter avec un stockage vide."""
        self._entries: list[AuditEntry] = []

    async def log(self, entry: AuditEntry) -> None:
        """Enregistre une entrée d'audit en mémoire.

        Args:
            entry: L'entrée d'audit à enregistrer
        """
        self._entries.append(entry)

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
        entry = AuditEntry(
            event_type="request",
            request_id=request_id,
            app_id=app_id,
            model=model,
            outcome=outcome,
            details=details or {},
        )
        await self.log(entry)

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
        entry = AuditEntry(
            event_type="policy_decision",
            request_id=request_id,
            app_id=app_id,
            action=action,
            details={
                "policy_id": policy_id,
                "reason": reason,
            },
        )
        await self.log(entry)

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
        entries = self._entries.copy()

        # Apply filters
        if app_id:
            entries = [e for e in entries if e.app_id == app_id]

        if org_id:
            entries = [e for e in entries if e.org_id == org_id]

        if event_type:
            entries = [e for e in entries if e.event_type == event_type]

        if start_time:
            entries = [e for e in entries if e.timestamp >= start_time]

        if end_time:
            entries = [e for e in entries if e.timestamp <= end_time]

        # Sort by timestamp descending and limit
        entries.sort(key=lambda e: e.timestamp, reverse=True)

        return entries[:limit]

    def clear(self) -> None:
        """Vide toutes les entrées d'audit."""
        self._entries.clear()

    @property
    def entries(self) -> list[AuditEntry]:
        """Accès direct aux entrées pour les tests."""
        return self._entries
