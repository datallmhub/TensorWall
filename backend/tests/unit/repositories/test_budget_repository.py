"""Unit tests for BudgetRepository."""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from backend.db.models import Base, Application, BudgetPeriod, BudgetScope
from backend.db.repositories.budget import BudgetRepository
from backend.db.repositories.application import ApplicationRepository


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def engine():
    """Create a test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def session(engine) -> AsyncSession:
    """Create a test database session."""
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session


@pytest_asyncio.fixture
async def repo(session: AsyncSession) -> BudgetRepository:
    """Create a BudgetRepository instance."""
    return BudgetRepository(session)


@pytest_asyncio.fixture
async def app_repo(session: AsyncSession) -> ApplicationRepository:
    """Create an ApplicationRepository instance."""
    return ApplicationRepository(session)


@pytest_asyncio.fixture
async def test_app(
    app_repo: ApplicationRepository, session: AsyncSession
) -> Application:
    """Create a test application."""
    app = await app_repo.create(
        app_id="test-app",
        name="Test Application",
        owner="test-team",
    )
    await session.commit()
    return app


class TestBudgetRepositoryCreate:
    """Tests for BudgetRepository create methods."""

    @pytest.mark.asyncio
    async def test_create_basic(self, repo: BudgetRepository, session: AsyncSession):
        """Test creating a basic budget."""
        budget = await repo.create(
            soft_limit_usd=50.0,
            hard_limit_usd=100.0,
        )
        await session.commit()

        assert budget.id is not None
        assert budget.soft_limit_usd == 50.0
        assert budget.hard_limit_usd == 100.0
        assert budget.scope == BudgetScope.APPLICATION

    @pytest.mark.asyncio
    async def test_create_app_budget(
        self, repo: BudgetRepository, test_app: Application, session: AsyncSession
    ):
        """Test creating an application budget."""
        budget = await repo.create_app_budget(
            application_id=test_app.id,
            soft_limit_usd=50.0,
            hard_limit_usd=100.0,
        )
        await session.commit()

        assert budget.scope == BudgetScope.APPLICATION
        assert budget.application_id == test_app.id

    @pytest.mark.asyncio
    async def test_create_user_budget(
        self, repo: BudgetRepository, session: AsyncSession
    ):
        """Test creating a user budget."""
        budget = await repo.create_user_budget(
            user_email="user@example.com",
            soft_limit_usd=25.0,
            hard_limit_usd=50.0,
        )
        await session.commit()

        assert budget.scope == BudgetScope.USER
        assert budget.user_email == "user@example.com"

    @pytest.mark.asyncio
    async def test_create_org_budget(
        self, repo: BudgetRepository, session: AsyncSession
    ):
        """Test creating an organization budget."""
        budget = await repo.create_org_budget(
            org_id="org-123",
            soft_limit_usd=500.0,
            hard_limit_usd=1000.0,
        )
        await session.commit()

        assert budget.scope == BudgetScope.ORGANIZATION
        assert budget.org_id == "org-123"


class TestBudgetRepositoryRead:
    """Tests for BudgetRepository read methods."""

    @pytest.mark.asyncio
    async def test_get_by_id(self, repo: BudgetRepository, session: AsyncSession):
        """Test getting a budget by ID."""
        budget = await repo.create(soft_limit_usd=50.0, hard_limit_usd=100.0)
        await session.commit()

        found = await repo.get_by_id(budget.id)

        assert found is not None
        assert found.id == budget.id

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repo: BudgetRepository):
        """Test getting a non-existent budget."""
        found = await repo.get_by_id(9999)

        assert found is None

    @pytest.mark.asyncio
    async def test_get_by_uuid(self, repo: BudgetRepository, session: AsyncSession):
        """Test getting a budget by UUID."""
        budget = await repo.create(soft_limit_usd=50.0, hard_limit_usd=100.0)
        await session.commit()

        found = await repo.get_by_uuid(budget.uuid)

        assert found is not None
        assert found.id == budget.id


class TestBudgetRepositoryList:
    """Tests for BudgetRepository list methods."""

    @pytest.mark.asyncio
    async def test_list_by_application(
        self, repo: BudgetRepository, test_app: Application, session: AsyncSession
    ):
        """Test listing budgets by application."""
        await repo.create_app_budget(
            application_id=test_app.id,
            soft_limit_usd=50.0,
            hard_limit_usd=100.0,
        )
        await repo.create_app_budget(
            application_id=test_app.id,
            soft_limit_usd=25.0,
            hard_limit_usd=50.0,
            feature="chat",
        )
        await session.commit()

        budgets = await repo.list_by_application(test_app.id)

        assert len(budgets) == 2

    @pytest.mark.asyncio
    async def test_list_by_user(self, repo: BudgetRepository, session: AsyncSession):
        """Test listing budgets by user."""
        await repo.create_user_budget(
            user_email="user@example.com",
            soft_limit_usd=25.0,
            hard_limit_usd=50.0,
        )
        await repo.create_user_budget(
            user_email="user@example.com",
            soft_limit_usd=10.0,
            hard_limit_usd=20.0,
        )
        await session.commit()

        budgets = await repo.list_by_user("user@example.com")

        assert len(budgets) == 2

    @pytest.mark.asyncio
    async def test_list_by_org(self, repo: BudgetRepository, session: AsyncSession):
        """Test listing budgets by organization."""
        await repo.create_org_budget(
            org_id="org-123",
            soft_limit_usd=500.0,
            hard_limit_usd=1000.0,
        )
        await session.commit()

        budgets = await repo.list_by_org("org-123")

        assert len(budgets) == 1

    @pytest.mark.asyncio
    async def test_list_all(self, repo: BudgetRepository, session: AsyncSession):
        """Test listing all budgets."""
        await repo.create(soft_limit_usd=50.0, hard_limit_usd=100.0)
        await repo.create(soft_limit_usd=25.0, hard_limit_usd=50.0)
        await session.commit()

        budgets = await repo.list_all()

        assert len(budgets) == 2


class TestBudgetRepositoryUpdate:
    """Tests for BudgetRepository update methods."""

    @pytest.mark.asyncio
    async def test_update_limits(self, repo: BudgetRepository, session: AsyncSession):
        """Test updating budget limits."""
        budget = await repo.create(soft_limit_usd=50.0, hard_limit_usd=100.0)
        await session.commit()

        updated = await repo.update(
            id=budget.id,
            soft_limit_usd=75.0,
            hard_limit_usd=150.0,
        )
        await session.commit()

        assert updated.soft_limit_usd == 75.0
        assert updated.hard_limit_usd == 150.0

    @pytest.mark.asyncio
    async def test_update_nonexistent(self, repo: BudgetRepository):
        """Test updating a non-existent budget."""
        updated = await repo.update(id=9999, soft_limit_usd=100.0)

        assert updated is None

    @pytest.mark.asyncio
    async def test_record_usage(self, repo: BudgetRepository, session: AsyncSession):
        """Test recording usage against a budget."""
        budget = await repo.create(soft_limit_usd=50.0, hard_limit_usd=100.0)
        await session.commit()

        updated = await repo.record_usage(id=budget.id, cost_usd=10.0)
        await session.commit()

        assert updated.current_spend_usd == 10.0

        updated = await repo.record_usage(id=budget.id, cost_usd=5.0)
        await session.commit()

        assert updated.current_spend_usd == 15.0

    @pytest.mark.asyncio
    async def test_reset_budget(self, repo: BudgetRepository, session: AsyncSession):
        """Test resetting a budget."""
        budget = await repo.create(soft_limit_usd=50.0, hard_limit_usd=100.0)
        budget.current_spend_usd = 80.0
        await session.commit()

        reset = await repo.reset_budget(budget.id)
        await session.commit()

        assert reset.current_spend_usd == 0.0


class TestBudgetRepositoryDelete:
    """Tests for BudgetRepository delete methods."""

    @pytest.mark.asyncio
    async def test_delete(self, repo: BudgetRepository, session: AsyncSession):
        """Test deleting a budget."""
        budget = await repo.create(soft_limit_usd=50.0, hard_limit_usd=100.0)
        await session.commit()

        result = await repo.delete(budget.id)
        await session.commit()

        assert result is True

        found = await repo.get_by_id(budget.id)
        assert found is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, repo: BudgetRepository):
        """Test deleting a non-existent budget."""
        result = await repo.delete(9999)

        assert result is False


class TestBudgetPeriodReset:
    """Tests for budget period reset functionality."""

    @pytest.mark.asyncio
    async def test_hourly_budget_reset(
        self, repo: BudgetRepository, session: AsyncSession
    ):
        """Test hourly budget period reset."""
        budget = await repo.create(
            soft_limit_usd=50.0,
            hard_limit_usd=100.0,
            period=BudgetPeriod.HOURLY,
        )
        budget.current_spend_usd = 50.0
        budget.period_start = datetime.utcnow() - timedelta(hours=2)
        await session.commit()

        # Recording usage should trigger period check
        await repo.record_usage(budget.id, 5.0)
        await session.commit()

        # Budget should have been reset
        found = await repo.get_by_id(budget.id)
        assert found.current_spend_usd == 5.0  # Only the new charge

    @pytest.mark.asyncio
    async def test_daily_budget_no_reset(
        self, repo: BudgetRepository, session: AsyncSession
    ):
        """Test that daily budget doesn't reset before period ends."""
        budget = await repo.create(
            soft_limit_usd=50.0,
            hard_limit_usd=100.0,
            period=BudgetPeriod.DAILY,
        )
        budget.current_spend_usd = 50.0
        budget.period_start = datetime.utcnow() - timedelta(hours=12)
        await session.commit()

        await repo.record_usage(budget.id, 5.0)
        await session.commit()

        found = await repo.get_by_id(budget.id)
        assert found.current_spend_usd == 55.0  # Should accumulate
