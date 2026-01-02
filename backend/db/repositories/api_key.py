"""API Key repository."""

import hashlib
import secrets
from typing import Optional
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db.models import ApiKey, Environment


def hash_api_key(key: str) -> str:
    """Hash an API key using SHA256."""
    return hashlib.sha256(key.encode()).hexdigest()


def generate_api_key(prefix: str = "gw") -> str:
    """Generate a new API key."""
    random_part = secrets.token_urlsafe(32)
    return f"{prefix}_{random_part}"


class ApiKeyRepository:
    """Repository for API Key CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        application_id: int,
        name: str,
        environment: Environment = Environment.DEVELOPMENT,
        llm_api_key: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> tuple[ApiKey, str]:
        """
        Create a new API key.
        Returns tuple of (ApiKey model, raw key string).
        The raw key is only available at creation time.
        """
        raw_key = generate_api_key()
        key_hash = hash_api_key(raw_key)
        key_prefix = raw_key[:12]

        # Encrypt LLM API key if provided (simple encoding for now - use proper encryption in prod)
        encrypted_llm_key = None
        if llm_api_key:
            # TODO: Use proper encryption (Fernet, KMS, etc.)
            encrypted_llm_key = llm_api_key  # Placeholder

        api_key = ApiKey(
            application_id=application_id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=name,
            environment=environment,
            llm_api_key_encrypted=encrypted_llm_key,
            expires_at=expires_at,
        )
        self.session.add(api_key)
        await self.session.flush()

        return api_key, raw_key

    async def get_by_key(self, raw_key: str) -> Optional[ApiKey]:
        """Get API key by raw key value."""
        key_hash = hash_api_key(raw_key)
        result = await self.session.execute(
            select(ApiKey)
            .options(selectinload(ApiKey.application))
            .where(ApiKey.key_hash == key_hash)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, id: int) -> Optional[ApiKey]:
        """Get API key by ID."""
        result = await self.session.execute(
            select(ApiKey)
            .options(selectinload(ApiKey.application))
            .where(ApiKey.id == id)
        )
        return result.scalar_one_or_none()

    async def list_by_application(
        self,
        application_id: int,
        active_only: bool = True,
    ) -> list[ApiKey]:
        """List all API keys for an application."""
        query = select(ApiKey).where(ApiKey.application_id == application_id)
        if active_only:
            query = query.where(ApiKey.is_active.is_(True))
        query = query.order_by(ApiKey.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def validate_key(self, raw_key: str) -> Optional[ApiKey]:
        """Validate an API key and return it if valid."""
        api_key = await self.get_by_key(raw_key)

        if not api_key:
            return None

        if not api_key.is_active:
            return None

        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            return None

        if not api_key.application.is_active:
            return None

        # Update last used timestamp
        api_key.last_used_at = datetime.utcnow()
        await self.session.flush()

        return api_key

    async def deactivate(self, id: int) -> bool:
        """Deactivate an API key."""
        api_key = await self.get_by_id(id)
        if not api_key:
            return False

        api_key.is_active = False
        await self.session.flush()
        return True

    async def rotate(
        self,
        id: int,
        name: Optional[str] = None,
    ) -> Optional[tuple[ApiKey, str]]:
        """
        Rotate an API key - creates a new key and deactivates the old one.
        Returns tuple of (new ApiKey, raw key string).
        """
        old_key = await self.get_by_id(id)
        if not old_key:
            return None

        # Create new key with same settings
        new_key, raw_key = await self.create(
            application_id=old_key.application_id,
            name=name or f"{old_key.name} (rotated)",
            environment=old_key.environment,
            llm_api_key=old_key.llm_api_key_encrypted,  # Copy encrypted key
            expires_at=old_key.expires_at,
        )

        # Deactivate old key
        old_key.is_active = False
        await self.session.flush()

        return new_key, raw_key

    async def delete(self, id: int) -> bool:
        """Permanently delete an API key."""
        api_key = await self.get_by_id(id)
        if not api_key:
            return False

        await self.session.delete(api_key)
        await self.session.flush()
        return True
