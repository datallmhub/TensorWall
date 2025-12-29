"""Application repository."""

from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db.models import Application


class ApplicationRepository:
    """Repository for Application CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        app_id: str,
        name: str,
        owner: str,
        description: Optional[str] = None,
        allowed_providers: Optional[list[str]] = None,
        allowed_models: Optional[list[str]] = None,
    ) -> Application:
        """Create a new application."""
        app = Application(
            app_id=app_id,
            name=name,
            owner=owner,
            description=description,
            allowed_providers=allowed_providers or ["openai", "anthropic"],
            allowed_models=allowed_models or [],
        )
        self.session.add(app)
        await self.session.flush()
        return app

    async def get_by_id(self, id: int) -> Optional[Application]:
        """Get application by internal ID (internal use only)."""
        result = await self.session.execute(select(Application).where(Application.id == id))
        return result.scalar_one_or_none()

    async def get_by_uuid(self, uuid: UUID) -> Optional[Application]:
        """Get application by UUID (public API use)."""
        result = await self.session.execute(select(Application).where(Application.uuid == uuid))
        return result.scalar_one_or_none()

    async def get_by_app_id(self, app_id: str) -> Optional[Application]:
        """Get application by app_id."""
        result = await self.session.execute(select(Application).where(Application.app_id == app_id))
        return result.scalar_one_or_none()

    async def get_by_app_id_with_relations(self, app_id: str) -> Optional[Application]:
        """Get application with all related data."""
        result = await self.session.execute(
            select(Application)
            .options(
                selectinload(Application.api_keys),
                selectinload(Application.budgets),
                selectinload(Application.policy_rules),
            )
            .where(Application.app_id == app_id)
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = True,
    ) -> list[Application]:
        """List all applications."""
        query = select(Application)
        if active_only:
            query = query.where(Application.is_active.is_(True))
        query = query.offset(skip).limit(limit).order_by(Application.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(
        self,
        app_id: str,
        name: Optional[str] = None,
        owner: Optional[str] = None,
        description: Optional[str] = None,
        allowed_providers: Optional[list[str]] = None,
        allowed_models: Optional[list[str]] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[Application]:
        """Update an application."""
        app = await self.get_by_app_id(app_id)
        if not app:
            return None

        if name is not None:
            app.name = name
        if owner is not None:
            app.owner = owner
        if description is not None:
            app.description = description
        if allowed_providers is not None:
            app.allowed_providers = allowed_providers
        if allowed_models is not None:
            app.allowed_models = allowed_models
        if is_active is not None:
            app.is_active = is_active

        await self.session.flush()
        return app

    async def delete(self, app_id: str) -> bool:
        """Delete an application (soft delete by deactivating)."""
        app = await self.get_by_app_id(app_id)
        if not app:
            return False

        app.is_active = False
        await self.session.flush()
        return True

    async def hard_delete(self, app_id: str) -> bool:
        """Permanently delete an application."""
        app = await self.get_by_app_id(app_id)
        if not app:
            return False

        await self.session.delete(app)
        await self.session.flush()
        return True
