"""
Authentication module with database integration.

Production-ready authentication with:
- Database API key lookup
- SHA256 key hashing
- Key expiration checking
- Rate limit integration
- Caching for performance
"""

from fastapi import HTTPException, Security, Header
from fastapi.security import APIKeyHeader
from typing import Optional
from pydantic import BaseModel
from datetime import datetime, timezone
import hashlib
import logging

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db_context
from backend.db.models import ApiKey
from backend.adapters.cache.redis_client import get_redis

logger = logging.getLogger(__name__)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Cache TTL for credentials (seconds)
CREDENTIALS_CACHE_TTL = 300  # 5 minutes


class AppCredentials(BaseModel):
    """Credentials d'une application cliente."""

    app_id: str
    api_key_id: int
    api_key_prefix: str
    owner: str
    environment: str
    created_at: datetime
    is_active: bool = True

    # LLM Provider credentials (passthrough)
    llm_api_key: Optional[str] = None  # Clé LLM du client (BYO-LA)
    allowed_providers: list[str] = ["openai", "anthropic"]
    allowed_models: list[str] = []  # Empty = all allowed

    class Config:
        from_attributes = True


class AuthResult(BaseModel):
    authenticated: bool
    app_id: Optional[str] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    credentials: Optional[AppCredentials] = None


def hash_api_key(api_key: str) -> str:
    """Hash an API key using SHA256."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def get_key_prefix(api_key: str) -> str:
    """Get the prefix of an API key for identification."""
    # Format: gw_xxxx_... -> return first 12 chars
    return api_key[:12] if len(api_key) >= 12 else api_key


async def get_credentials_from_cache(key_hash: str) -> Optional[dict]:
    """Get cached credentials from Redis."""
    try:
        redis = await get_redis()
        if redis:
            cached = await redis.get(f"auth:credentials:{key_hash}")
            if cached:
                import json

                return json.loads(cached)
    except Exception as e:
        logger.warning(f"Redis cache read failed: {e}")
    return None


async def cache_credentials(key_hash: str, credentials: dict) -> None:
    """Cache credentials in Redis."""
    try:
        redis = await get_redis()
        if redis:
            import json

            await redis.setex(
                f"auth:credentials:{key_hash}",
                CREDENTIALS_CACHE_TTL,
                json.dumps(credentials, default=str),
            )
    except Exception as e:
        logger.warning(f"Redis cache write failed: {e}")


async def invalidate_credentials_cache(key_hash: str) -> None:
    """Invalidate cached credentials."""
    try:
        redis = await get_redis()
        if redis:
            await redis.delete(f"auth:credentials:{key_hash}")
    except Exception as e:
        logger.warning(f"Redis cache invalidation failed: {e}")


async def lookup_credentials_db(api_key: str) -> Optional[AppCredentials]:
    """Look up credentials from database."""
    key_hash = hash_api_key(api_key)
    key_prefix = get_key_prefix(api_key)

    # Try cache first
    cached = await get_credentials_from_cache(key_hash)
    if cached:
        logger.debug(f"Credentials cache hit for key prefix: {key_prefix}")
        return AppCredentials(**cached)

    # Database lookup
    try:
        async with get_db_context() as db:
            stmt = (
                select(ApiKey)
                .options(selectinload(ApiKey.application))
                .where(ApiKey.key_hash == key_hash)
            )
            result = await db.execute(stmt)
            api_key_record = result.scalar_one_or_none()

            if not api_key_record:
                logger.warning(f"API key not found: {key_prefix}...")
                return None

            if not api_key_record.is_active:
                logger.warning(f"API key disabled: {key_prefix}...")
                return None

            if api_key_record.expires_at and api_key_record.expires_at < datetime.now(timezone.utc):
                logger.warning(f"API key expired: {key_prefix}...")
                return None

            app = api_key_record.application
            if not app or not app.is_active:
                logger.warning(f"Application disabled for key: {key_prefix}...")
                return None

            # Update last_used_at (use naive UTC for database compatibility)
            api_key_record.last_used_at = datetime.utcnow()
            await db.commit()

            credentials = AppCredentials(
                app_id=app.app_id,
                api_key_id=api_key_record.id,
                api_key_prefix=api_key_record.key_prefix,
                owner=app.owner,
                environment=api_key_record.environment.value,
                created_at=api_key_record.created_at,
                is_active=True,
                llm_api_key=None,  # Will be set from Authorization header
                allowed_providers=app.allowed_providers or ["openai", "anthropic"],
                allowed_models=app.allowed_models or [],
            )

            # Cache for next time
            await cache_credentials(key_hash, credentials.model_dump())

            return credentials

    except Exception as e:
        logger.error(f"Database lookup failed: {e}")
        return None


async def authenticate(
    api_key: Optional[str] = Security(api_key_header),
    authorization: Optional[str] = Header(None),
) -> AuthResult:
    """
    Authentifie une requête via la base de données.

    Supports:
    - X-API-Key header (gateway key)
    - Authorization: Bearer (LLM passthrough key)

    Process:
    1. Check for API key presence
    2. Hash the key and look up in database
    3. Validate key is active and not expired
    4. Load application settings
    5. Cache credentials for performance
    """
    if not api_key:
        return AuthResult(
            authenticated=False, error="Missing X-API-Key header", error_code="AUTH_MISSING_KEY"
        )

    # Database lookup only - no hardcoded fallback
    credentials = await lookup_credentials_db(api_key)

    if not credentials:
        logger.warning(f"API key not found in database: {get_key_prefix(api_key)}...")
        return AuthResult(
            authenticated=False, error="Invalid API key", error_code="AUTH_INVALID_KEY"
        )

    if not credentials.is_active:
        return AuthResult(
            authenticated=False, error="API key is deactivated", error_code="AUTH_KEY_DISABLED"
        )

    # Extract LLM key from Authorization header if not stored
    if authorization and authorization.startswith("Bearer "):
        credentials.llm_api_key = authorization.replace("Bearer ", "")

    return AuthResult(authenticated=True, app_id=credentials.app_id, credentials=credentials)


def require_auth(auth_result: AuthResult) -> AppCredentials:
    """Dependency that requires authentication."""
    if not auth_result.authenticated:
        raise HTTPException(
            status_code=401,
            detail={
                "error": auth_result.error_code or "AUTH_ERROR",
                "message": auth_result.error or "Authentication required",
            },
        )
    return auth_result.credentials


# =============================================================================
# API Key Management Functions
# =============================================================================


async def create_api_key(
    db: AsyncSession,
    application_id: int,
    name: str,
    environment: str = "development",
    expires_at: Optional[datetime] = None,
) -> tuple[str, ApiKey]:
    """
    Create a new API key for an application.

    Returns the raw key (only time it's visible) and the ApiKey record.
    """
    import secrets

    # Generate key: gw_<prefix>_<random>
    prefix = secrets.token_hex(4)  # 8 chars
    random_part = secrets.token_hex(16)  # 32 chars
    raw_key = f"gw_{prefix}_{random_part}"

    key_hash = hash_api_key(raw_key)
    key_prefix = get_key_prefix(raw_key)

    from backend.db.models import Environment as EnvEnum

    env_enum = EnvEnum(environment)

    api_key = ApiKey(
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=name,
        application_id=application_id,
        environment=env_enum,
        expires_at=expires_at,
        is_active=True,
    )

    db.add(api_key)
    await db.flush()

    logger.info(f"Created API key {key_prefix}... for application {application_id}")

    return raw_key, api_key


async def revoke_api_key(db: AsyncSession, key_id: int) -> bool:
    """Revoke an API key by ID."""
    stmt = select(ApiKey).where(ApiKey.id == key_id)
    result = await db.execute(stmt)
    api_key = result.scalar_one_or_none()

    if not api_key:
        return False

    api_key.is_active = False

    # Invalidate cache
    await invalidate_credentials_cache(api_key.key_hash)

    logger.info(f"Revoked API key {api_key.key_prefix}...")
    return True


async def rotate_api_key(
    db: AsyncSession,
    old_key_id: int,
    grace_period_hours: int = 24,
) -> Optional[tuple[str, ApiKey]]:
    """
    Rotate an API key - create new one and schedule old one for expiration.

    Returns the new raw key and ApiKey record.
    """
    # Get old key
    stmt = select(ApiKey).options(selectinload(ApiKey.application)).where(ApiKey.id == old_key_id)
    result = await db.execute(stmt)
    old_key = result.scalar_one_or_none()

    if not old_key:
        return None

    # Create new key
    from datetime import timedelta

    raw_key, new_key = await create_api_key(
        db=db,
        application_id=old_key.application_id,
        name=f"{old_key.name} (rotated)",
        environment=old_key.environment.value,
    )

    # Schedule old key expiration
    old_key.expires_at = datetime.now(timezone.utc) + timedelta(hours=grace_period_hours)

    # Invalidate cache for old key
    await invalidate_credentials_cache(old_key.key_hash)

    logger.info(f"Rotated API key {old_key.key_prefix}... -> {new_key.key_prefix}...")

    return raw_key, new_key
