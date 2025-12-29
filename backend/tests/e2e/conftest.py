"""Fixtures for E2E tests."""

import pytest
import pytest_asyncio
from typing import AsyncGenerator
from datetime import datetime, timezone, timedelta
import uuid
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from backend.main import app
from backend.db.models import (
    Base,
    Application,
    ApiKey,
    PolicyRule,
    Budget,
    Feature,
    LLMModel,
    UsageRecord,
    Organization,
    User,
    PolicyAction,
    LLMRequestTrace,
    AuditLog,
    AuditEventType,
    TraceDecision,
    TraceStatus,
    Environment,
    UserRole as UserRoleEnum,  # Rename to avoid conflict
)
from backend.core.jwt_auth import (
    hash_password,
    create_access_token,
    create_refresh_token,
    AuthenticatedUser,
    get_current_user,
)
from backend.db.session import get_db
from backend.core.auth import hash_api_key
from backend.core.jwt import get_current_user_id


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create a fresh test database for each test."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Create a test HTTP client with admin authentication.

    This client overrides auth dependencies to bypass permission checks
    and simulates a logged-in admin user for all tests by default.
    """

    async def override_get_db():
        yield db

    # Create a mock authenticated user for permission checks
    mock_authenticated_user = AuthenticatedUser(
        id=1,
        email="admin@test.com",
        name="Test Admin",
        role="admin",
        permissions=[
            "apps:read",
            "apps:write",
            "apps:delete",
            "keys:read",
            "keys:write",
            "keys:rotate",
            "keys:delete",
            "policies:read",
            "policies:write",
            "policies:delete",
            "budgets:read",
            "budgets:write",
            "budgets:reset",
            "analytics:read",
            "audit:read",
            "audit:export",
            "llm:chat",
            "llm:embeddings",
        ],
    )

    # Override get_current_user to return our mock admin (no params needed)
    def override_get_current_user():
        return mock_authenticated_user

    # Override get_current_user_id to return admin user id (no params needed)
    def override_get_current_user_id():
        return 1

    # Apply overrides
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_user_id] = override_get_current_user_id

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# =============================================================================
# Seed Data Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def seed_organization(db: AsyncSession) -> Organization:
    """Create a test organization."""
    from backend.db.models import TenantStatus, TenantTier

    org = Organization(
        org_id="test-org-001",
        name="Test Organization",
        slug="test-org",
        status=TenantStatus.ACTIVE,
        tier=TenantTier.PROFESSIONAL,
        owner_email="admin@test-org.com",
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


@pytest_asyncio.fixture
async def seed_application(db: AsyncSession) -> Application:
    """Create a test application with API key."""
    application = Application(
        app_id="test-app",
        name="Test Application",
        owner="test-team",
        description="E2E test application",
        allowed_providers=["openai", "anthropic"],
        allowed_models=["gpt-4o", "gpt-4o-mini", "claude-3-opus"],
        is_active=True,
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)
    return application


@pytest_asyncio.fixture
async def seed_api_key(db: AsyncSession, seed_application: Application) -> tuple[ApiKey, str]:
    """Create a test API key and return both the model and raw key."""
    raw_key = "gw_test_e2e_key_12345678901234567890"
    api_key = ApiKey(
        application_id=seed_application.id,
        key_hash=hash_api_key(raw_key),
        key_prefix=raw_key[:12],
        name="E2E Test Key",
        environment="development",
        is_active=True,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    return api_key, raw_key


@pytest_asyncio.fixture
async def seed_policy(db: AsyncSession, seed_application: Application) -> PolicyRule:
    """Create a test policy."""
    policy = PolicyRule(
        name="e2e-test-policy",
        description="E2E test policy",
        application_id=seed_application.id,
        conditions={
            "environments": ["production"],
            "max_tokens": 4000,
        },
        action=PolicyAction.DENY,
        priority=10,
        is_enabled=True,
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy


@pytest_asyncio.fixture
async def seed_budget(db: AsyncSession, seed_application: Application) -> Budget:
    """Create a test budget."""
    budget = Budget(
        application_id=seed_application.id,
        soft_limit_usd=50.0,
        hard_limit_usd=100.0,
        current_spend_usd=25.0,
        period="monthly",
        period_start=datetime.now(timezone.utc),
        is_active=True,
    )
    db.add(budget)
    await db.commit()
    await db.refresh(budget)
    return budget


@pytest_asyncio.fixture
async def seed_feature(db: AsyncSession, seed_application: Application) -> Feature:
    """Create a test feature."""
    feature = Feature(
        feature_id="chat",
        name="Chat Feature",
        description="Chat completion feature",
        app_id=seed_application.app_id,
        allowed_actions=["chat", "completion"],
        allowed_models=["gpt-4o", "gpt-4o-mini"],
        is_enabled=True,
    )
    db.add(feature)
    await db.commit()
    await db.refresh(feature)
    return feature


@pytest_asyncio.fixture
async def seed_model(db: AsyncSession) -> LLMModel:
    """Create a test LLM model."""
    from backend.db.models import ProviderType

    model = LLMModel(
        model_id="gpt-4o",
        provider=ProviderType.OPENAI,
        provider_model_id="gpt-4o-2024-08-06",
        name="GPT-4o",
        description="OpenAI GPT-4o model",
        input_cost_per_million=2.5,
        output_cost_per_million=10.0,
        context_length=128000,
        supports_vision=True,
        supports_functions=True,
        supports_streaming=True,
        is_enabled=True,
    )
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return model


@pytest_asyncio.fixture
async def seed_usage_log(
    db: AsyncSession,
    seed_application: Application,
    seed_model: LLMModel,
) -> UsageRecord:
    """Create a test usage record."""
    record = UsageRecord(
        request_id=str(uuid.uuid4()),
        app_id=seed_application.app_id,
        feature="chat",
        environment=Environment.DEVELOPMENT,
        provider="openai",
        model=seed_model.model_id,
        input_tokens=100,
        output_tokens=50,
        cost_usd=0.001,
        latency_ms=500,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@pytest_asyncio.fixture
async def auth_headers(seed_api_key: tuple[ApiKey, str]) -> dict:
    """Get authentication headers with API key."""
    _, raw_key = seed_api_key
    return {"X-API-Key": raw_key}


@pytest_asyncio.fixture
async def admin_headers() -> dict:
    """Get admin authentication headers (for admin endpoints)."""
    # For admin endpoints, we simulate admin auth
    # In production, this would be a JWT token
    return {"Authorization": "Bearer admin-test-token"}


@pytest_asyncio.fixture
async def seed_usage_logs(
    db: AsyncSession,
    seed_application: Application,
    seed_model: LLMModel,
) -> list[UsageRecord]:
    """Create multiple test usage records for analytics testing."""
    records = []
    now = datetime.now(timezone.utc)

    # Create records for the past 7 days
    for i in range(10):
        record = UsageRecord(
            request_id=str(uuid.uuid4()),
            app_id=seed_application.app_id,
            model=seed_model.model_id,
            provider="openai",
            feature="chat" if i % 2 == 0 else "completion",
            environment=Environment.DEVELOPMENT if i % 3 == 0 else Environment.PRODUCTION,
            input_tokens=100 + i * 10,
            output_tokens=50 + i * 5,
            cost_usd=0.001 + i * 0.0001,
            latency_ms=200 + i * 20,
            created_at=now - timedelta(days=i % 7),
        )
        records.append(record)
        db.add(record)

    await db.commit()
    for record in records:
        await db.refresh(record)
    return records


@pytest_asyncio.fixture
async def seed_traces(
    db: AsyncSession,
    seed_application: Application,
) -> list[LLMRequestTrace]:
    """Create multiple test request traces for analytics testing."""
    traces = []
    now = datetime.utcnow()

    for i in range(5):
        trace = LLMRequestTrace(
            request_id=str(uuid.uuid4()),
            app_id=seed_application.app_id,
            feature="chat" if i % 2 == 0 else "completion",
            environment=Environment.DEVELOPMENT if i % 3 == 0 else Environment.PRODUCTION,
            provider="openai",
            model="gpt-4o",
            input_tokens=100 + i * 10,
            output_tokens=50 + i * 5,
            cost_usd=0.001 + i * 0.0001,
            decision=TraceDecision.ALLOW if i % 3 != 2 else TraceDecision.BLOCK,
            decision_reasons=["budget_ok"] if i % 3 != 2 else ["budget_exceeded"],
            risk_categories=[],
            policies_evaluated=[],
            latency_ms=200 + i * 20,
            status=TraceStatus.SUCCESS if i % 3 != 2 else TraceStatus.BLOCKED,
            timestamp_start=now - timedelta(hours=i),
            timestamp_end=now - timedelta(hours=i) + timedelta(milliseconds=200 + i * 20),
        )
        traces.append(trace)
        db.add(trace)

    await db.commit()
    for trace in traces:
        await db.refresh(trace)
    return traces


@pytest_asyncio.fixture
async def seed_audit_logs(
    db: AsyncSession,
    seed_application: Application,
) -> list[AuditLog]:
    """Create multiple test audit logs."""
    logs = []
    now = datetime.utcnow()

    for i in range(5):
        log = AuditLog(
            event_type=AuditEventType.REQUEST if i % 3 != 2 else AuditEventType.ERROR,
            request_id=str(uuid.uuid4()),
            app_id=seed_application.app_id,
            feature="chat",
            environment="development",
            model="gpt-4o",
            provider="openai",
            policy_decision="allow" if i % 2 == 0 else "deny",
            blocked=i % 2 != 0,
            timestamp=now - timedelta(hours=i),
        )
        logs.append(log)
        db.add(log)

    await db.commit()
    for log in logs:
        await db.refresh(log)
    return logs


@pytest_asyncio.fixture
async def seed_user_with_password(db: AsyncSession) -> User:
    """Create a test user with password for auth testing."""
    user = User(
        email="testuser@example.com",
        name="Test User",
        password_hash=hash_password("testpassword123"),
        role=UserRoleEnum.DEVELOPER,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def seed_admin_user(db: AsyncSession) -> User:
    """Create an admin user with full permissions for testing."""
    user = User(
        email="admin@test.com",
        name="Test Admin",
        password_hash=hash_password("adminpassword123"),
        role=UserRoleEnum.ADMIN,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_cookies() -> dict:
    """Get authentication cookies (placeholder for JWT-based tests)."""
    # In real tests, you would login and get cookies
    # This is a placeholder that tests can use
    return {"access_token": "test-token", "refresh_token": "test-refresh"}


# =============================================================================
# Authenticated Client Fixtures (with JWT auth)
# =============================================================================


@pytest_asyncio.fixture
async def authenticated_client(
    db: AsyncSession,
    seed_admin_user: User,
) -> AsyncGenerator[AsyncClient, None]:
    """
    Create an authenticated HTTP client with admin JWT token.

    This client overrides auth dependencies to bypass permission checks
    and simulates a logged-in admin user.
    """

    async def override_get_db():
        yield db

    # Create a mock authenticated user for permission checks
    mock_authenticated_user = AuthenticatedUser(
        id=seed_admin_user.id,
        email=seed_admin_user.email,
        name=seed_admin_user.name,
        role="admin",
        permissions=[
            "apps:read",
            "apps:write",
            "apps:delete",
            "keys:read",
            "keys:write",
            "keys:rotate",
            "keys:delete",
            "policies:read",
            "policies:write",
            "policies:delete",
            "budgets:read",
            "budgets:write",
            "budgets:reset",
            "analytics:read",
            "audit:read",
            "audit:export",
            "llm:chat",
            "llm:embeddings",
        ],
    )

    # Override get_current_user to return our mock admin
    async def override_get_current_user(*args, **kwargs):
        return mock_authenticated_user

    # Override get_current_user_id to return admin user id
    async def override_get_current_user_id(*args, **kwargs):
        return seed_admin_user.id

    # Apply overrides
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_user_id] = override_get_current_user_id

    # Generate real JWT tokens for cookie-based auth
    access_token = create_access_token(seed_admin_user)
    refresh_token = create_refresh_token(seed_admin_user)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies={
            "access_token": access_token,
            "refresh_token": refresh_token,
        },
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_auth_headers(seed_admin_user: User) -> dict:
    """Get admin authentication headers with valid JWT token."""
    access_token = create_access_token(seed_admin_user)
    return {
        "Authorization": f"Bearer {access_token}",
    }


@pytest_asyncio.fixture
async def user_auth_headers(seed_user_with_password: User) -> dict:
    """Get regular user authentication headers with valid JWT token."""
    access_token = create_access_token(seed_user_with_password)
    return {
        "Authorization": f"Bearer {access_token}",
    }
