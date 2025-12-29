"""PostgreSQL Model Registry Adapter.

Architecture Hexagonale: Implémentation persistante du ModelRegistryPort
utilisant PostgreSQL pour le stockage du catalogue de modèles.

Ce module fournit:
- Stockage persistant des modèles
- Synchronisation avec providers externes
- Cache local pour performance
- Versioning des modèles
"""

from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ports.model_registry import (
    ModelRegistryPort,
    ModelInfo,
    ModelPricing,
    ModelLimits,
    ModelValidation,
    ProviderType,
    ModelStatus,
    ModelCapability,
)


class PostgresModelRegistryAdapter(ModelRegistryPort):
    """
    PostgreSQL-backed model registry implementation.

    Stores model catalog in database with caching layer.
    Supports dynamic model discovery and versioning.
    """

    def __init__(
        self,
        session_factory: Any,
        table_name: str = "model_registry",
        cache_ttl_seconds: int = 300,
    ):
        """
        Initialize PostgreSQL adapter.

        Args:
            session_factory: SQLAlchemy async session factory
            table_name: Name of the model registry table
            cache_ttl_seconds: Cache TTL in seconds
        """
        self._session_factory = session_factory
        self._table_name = table_name
        self._cache_ttl = cache_ttl_seconds

        # Local cache
        self._cache: dict[str, ModelInfo] = {}
        self._cache_time: datetime | None = None
        self._aliases: dict[str, str] = {}

    async def _get_session(self) -> AsyncSession:
        """Get a database session."""
        return self._session_factory()

    async def _ensure_table(self, session: AsyncSession) -> None:
        """Ensure the model registry table exists."""
        await session.execute(
            text(f"""
            CREATE TABLE IF NOT EXISTS {self._table_name} (
                model_id VARCHAR(255) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                provider VARCHAR(50) NOT NULL,
                provider_model_id VARCHAR(255) NOT NULL,
                description TEXT,
                capabilities JSONB DEFAULT '[]',
                input_per_million DECIMAL(10, 6) DEFAULT 0,
                output_per_million DECIMAL(10, 6) DEFAULT 0,
                max_context_tokens INTEGER DEFAULT 0,
                max_output_tokens INTEGER DEFAULT 0,
                max_images INTEGER,
                status VARCHAR(50) DEFAULT 'available',
                tags JSONB DEFAULT '[]',
                metadata JSONB DEFAULT '{{}}',
                base_url VARCHAR(500),
                added_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                deprecated_at TIMESTAMP
            )
        """)
        )
        await session.commit()

    async def _refresh_cache(self) -> None:
        """Refresh the local cache from database."""
        now = datetime.now()
        if self._cache_time and (now - self._cache_time).total_seconds() < self._cache_ttl:
            return

        async with await self._get_session() as session:
            await self._ensure_table(session)
            result = await session.execute(
                text(f"""
                SELECT model_id, name, provider, provider_model_id, description,
                       capabilities, input_per_million, output_per_million,
                       max_context_tokens, max_output_tokens, max_images,
                       status, tags, metadata, base_url, added_at, updated_at, deprecated_at
                FROM {self._table_name}
            """)
            )

            self._cache.clear()
            for row in result.fetchall():
                model = self._row_to_model(row)
                self._cache[model.model_id] = model

            self._cache_time = now

    def _row_to_model(self, row: Any) -> ModelInfo:
        """Convert a database row to ModelInfo."""
        capabilities = [
            ModelCapability(c)
            for c in (row[5] or [])
            if c in [cap.value for cap in ModelCapability]
        ]

        return ModelInfo(
            model_id=row[0],
            name=row[1],
            provider=ProviderType(row[2]),
            provider_model_id=row[3],
            description=row[4] or "",
            capabilities=capabilities,
            pricing=ModelPricing(
                input_per_million=float(row[6] or 0),
                output_per_million=float(row[7] or 0),
            ),
            limits=ModelLimits(
                max_context_tokens=row[8] or 0,
                max_output_tokens=row[9] or 0,
                max_images=row[10],
            ),
            status=ModelStatus(row[11]) if row[11] else ModelStatus.AVAILABLE,
            tags=row[12] or [],
            metadata=row[13] or {},
            base_url=row[14],
            added_at=row[15],
            updated_at=row[16],
            deprecated_at=row[17],
        )

    async def list_models(
        self,
        provider: ProviderType | None = None,
        capability: ModelCapability | None = None,
        status: ModelStatus | None = None,
        tags: list[str] | None = None,
    ) -> list[ModelInfo]:
        """List models with optional filters."""
        await self._refresh_cache()

        results = list(self._cache.values())

        if provider:
            results = [m for m in results if m.provider == provider]
        if capability:
            results = [m for m in results if capability in m.capabilities]
        if status:
            results = [m for m in results if m.status == status]
        if tags:
            results = [m for m in results if any(t in m.tags for t in tags)]

        return sorted(results, key=lambda m: m.name)

    async def get_model(
        self,
        model_id: str,
    ) -> ModelInfo | None:
        """Get a model by ID."""
        await self._refresh_cache()

        if model_id in self._cache:
            return self._cache[model_id]

        # Try alias
        resolved = await self.resolve_model_alias(model_id)
        if resolved and resolved in self._cache:
            return self._cache[resolved]

        return None

    async def get_model_by_provider_id(
        self,
        provider: ProviderType,
        provider_model_id: str,
    ) -> ModelInfo | None:
        """Get a model by provider ID."""
        await self._refresh_cache()

        for model in self._cache.values():
            if model.provider == provider and model.provider_model_id == provider_model_id:
                return model
        return None

    async def validate_model(
        self,
        model_id: str,
        capability: ModelCapability | None = None,
    ) -> ModelValidation:
        """Validate a model."""
        model = await self.get_model(model_id)

        if not model:
            suggested = None
            for m in self._cache.values():
                if model_id.lower() in m.model_id.lower():
                    suggested = m.model_id
                    break

            return ModelValidation(
                valid=False,
                model_id=model_id,
                reason=f"Model '{model_id}' not found",
                suggested_model=suggested,
            )

        if model.status == ModelStatus.UNAVAILABLE:
            return ModelValidation(
                valid=False,
                model_id=model_id,
                provider=model.provider,
                reason="Model is currently unavailable",
            )

        if model.status == ModelStatus.DEPRECATED:
            suggested = model.metadata.get("replacement")
            return ModelValidation(
                valid=True,
                model_id=model_id,
                provider=model.provider,
                reason="Model is deprecated",
                suggested_model=suggested,
            )

        if capability and capability not in model.capabilities:
            return ModelValidation(
                valid=False,
                model_id=model_id,
                provider=model.provider,
                reason=f"Model does not support capability: {capability.value}",
            )

        return ModelValidation(
            valid=True,
            model_id=model_id,
            provider=model.provider,
        )

    async def resolve_model_alias(
        self,
        alias: str,
    ) -> str | None:
        """Resolve a model alias."""
        if alias in self._cache:
            return alias
        return self._aliases.get(alias)

    async def register_model(
        self,
        model: ModelInfo,
    ) -> ModelInfo:
        """Register a new model."""
        async with await self._get_session() as session:
            await self._ensure_table(session)

            capabilities = [c.value for c in model.capabilities]
            now = datetime.now()

            await session.execute(
                text(f"""
                INSERT INTO {self._table_name} (
                    model_id, name, provider, provider_model_id, description,
                    capabilities, input_per_million, output_per_million,
                    max_context_tokens, max_output_tokens, max_images,
                    status, tags, metadata, base_url, added_at, updated_at
                ) VALUES (
                    :model_id, :name, :provider, :provider_model_id, :description,
                    :capabilities, :input_per_million, :output_per_million,
                    :max_context_tokens, :max_output_tokens, :max_images,
                    :status, :tags, :metadata, :base_url, :added_at, :updated_at
                )
                ON CONFLICT (model_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    provider = EXCLUDED.provider,
                    provider_model_id = EXCLUDED.provider_model_id,
                    description = EXCLUDED.description,
                    capabilities = EXCLUDED.capabilities,
                    input_per_million = EXCLUDED.input_per_million,
                    output_per_million = EXCLUDED.output_per_million,
                    max_context_tokens = EXCLUDED.max_context_tokens,
                    max_output_tokens = EXCLUDED.max_output_tokens,
                    max_images = EXCLUDED.max_images,
                    status = EXCLUDED.status,
                    tags = EXCLUDED.tags,
                    metadata = EXCLUDED.metadata,
                    base_url = EXCLUDED.base_url,
                    updated_at = EXCLUDED.updated_at
            """),
                {
                    "model_id": model.model_id,
                    "name": model.name,
                    "provider": model.provider.value,
                    "provider_model_id": model.provider_model_id,
                    "description": model.description,
                    "capabilities": capabilities,
                    "input_per_million": model.pricing.input_per_million,
                    "output_per_million": model.pricing.output_per_million,
                    "max_context_tokens": model.limits.max_context_tokens,
                    "max_output_tokens": model.limits.max_output_tokens,
                    "max_images": model.limits.max_images,
                    "status": model.status.value,
                    "tags": model.tags,
                    "metadata": model.metadata,
                    "base_url": model.base_url,
                    "added_at": now,
                    "updated_at": now,
                },
            )
            await session.commit()

        # Update cache
        model.added_at = now
        model.updated_at = now
        self._cache[model.model_id] = model

        return model

    async def update_model(
        self,
        model_id: str,
        status: ModelStatus | None = None,
        pricing: ModelPricing | None = None,
        limits: ModelLimits | None = None,
        tags: list[str] | None = None,
    ) -> ModelInfo:
        """Update a model."""
        model = await self.get_model(model_id)
        if not model:
            raise ValueError(f"Model {model_id} not found")

        async with await self._get_session() as session:
            updates = ["updated_at = NOW()"]
            params: dict[str, Any] = {"model_id": model_id}

            if status:
                updates.append("status = :status")
                params["status"] = status.value
                model.status = status

            if pricing:
                updates.append("input_per_million = :input_per_million")
                updates.append("output_per_million = :output_per_million")
                params["input_per_million"] = pricing.input_per_million
                params["output_per_million"] = pricing.output_per_million
                model.pricing = pricing

            if limits:
                updates.append("max_context_tokens = :max_context_tokens")
                updates.append("max_output_tokens = :max_output_tokens")
                updates.append("max_images = :max_images")
                params["max_context_tokens"] = limits.max_context_tokens
                params["max_output_tokens"] = limits.max_output_tokens
                params["max_images"] = limits.max_images
                model.limits = limits

            if tags:
                updates.append("tags = :tags")
                params["tags"] = tags
                model.tags = tags

            await session.execute(
                text(f"""
                UPDATE {self._table_name}
                SET {", ".join(updates)}
                WHERE model_id = :model_id
            """),
                params,
            )
            await session.commit()

        model.updated_at = datetime.now()
        self._cache[model_id] = model

        return model

    async def deprecate_model(
        self,
        model_id: str,
        suggested_replacement: str | None = None,
    ) -> ModelInfo:
        """Deprecate a model."""
        model = await self.get_model(model_id)
        if not model:
            raise ValueError(f"Model {model_id} not found")

        now = datetime.now()
        metadata = model.metadata.copy()
        if suggested_replacement:
            metadata["replacement"] = suggested_replacement

        async with await self._get_session() as session:
            await session.execute(
                text(f"""
                UPDATE {self._table_name}
                SET status = 'deprecated',
                    deprecated_at = :deprecated_at,
                    updated_at = :updated_at,
                    metadata = :metadata
                WHERE model_id = :model_id
            """),
                {
                    "model_id": model_id,
                    "deprecated_at": now,
                    "updated_at": now,
                    "metadata": metadata,
                },
            )
            await session.commit()

        model.status = ModelStatus.DEPRECATED
        model.deprecated_at = now
        model.updated_at = now
        model.metadata = metadata
        self._cache[model_id] = model

        return model

    async def remove_model(
        self,
        model_id: str,
    ) -> bool:
        """Remove a model."""
        async with await self._get_session() as session:
            result = await session.execute(
                text(f"""
                DELETE FROM {self._table_name}
                WHERE model_id = :model_id
            """),
                {"model_id": model_id},
            )
            await session.commit()

            if result.rowcount > 0:
                self._cache.pop(model_id, None)
                return True
            return False

    async def discover_local_models(
        self,
        provider: ProviderType,
        base_url: str | None = None,
    ) -> list[ModelInfo]:
        """Discover local models (not supported in PostgreSQL adapter)."""
        # Local discovery is not applicable for database storage
        return []

    async def sync_provider_models(
        self,
        provider: ProviderType,
    ) -> int:
        """Sync models from a provider (no-op for PostgreSQL)."""
        return 0

    async def estimate_cost(
        self,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Estimate cost for a request."""
        model = await self.get_model(model_id)
        if not model:
            return 0.0

        input_cost = (input_tokens / 1_000_000) * model.pricing.input_per_million
        output_cost = (output_tokens / 1_000_000) * model.pricing.output_per_million

        return input_cost + output_cost

    async def get_pricing(
        self,
        model_id: str,
    ) -> ModelPricing | None:
        """Get pricing for a model."""
        model = await self.get_model(model_id)
        return model.pricing if model else None

    def add_alias(self, alias: str, model_id: str) -> None:
        """Add a model alias."""
        self._aliases[alias] = model_id

    def invalidate_cache(self) -> None:
        """Invalidate the local cache."""
        self._cache.clear()
        self._cache_time = None
