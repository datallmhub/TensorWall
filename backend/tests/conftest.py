"""Pytest fixtures for TensorWall tests."""

import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from backend.main import app
from backend.db.models import Base
from backend.db.session import get_db
from backend.core.jwt_auth import AuthenticatedUser, get_current_user
from backend.core.jwt import get_current_user_id


# Use SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(test_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Create a test client with overridden database session and admin authentication.

    This client bypasses all authentication and permission checks.
    """

    async def override_get_db():
        yield test_session

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


@pytest.fixture
def sample_application_data():
    """Sample application data for tests."""
    return {
        "app_id": "test-app",
        "name": "Test Application",
        "owner": "test-team",
        "description": "A test application",
        "allowed_providers": ["openai", "anthropic"],
        "allowed_models": ["gpt-4o-mini", "gpt-4o"],
    }


@pytest.fixture
def sample_policy_data():
    """Sample policy data for tests."""
    return {
        "name": "test-policy",
        "description": "A test policy",
        "conditions": {
            "environments": ["production"],
            "max_tokens": 4000,
        },
        "action": "deny",
        "priority": 10,
    }


@pytest.fixture
def sample_budget_data():
    """Sample budget data for tests."""
    return {
        "app_id": "test-app",
        "soft_limit_usd": 50.0,
        "hard_limit_usd": 100.0,
        "period": "monthly",
    }
