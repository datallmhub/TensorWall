"""Unit tests for ApplicationRepository."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from backend.db.models import Base
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
async def repo(session: AsyncSession) -> ApplicationRepository:
    """Create an ApplicationRepository instance."""
    return ApplicationRepository(session)


class TestApplicationRepository:
    """Tests for ApplicationRepository."""

    @pytest.mark.asyncio
    async def test_create_application(self, repo: ApplicationRepository, session: AsyncSession):
        """Test creating an application."""
        app = await repo.create(
            app_id="test-app",
            name="Test Application",
            owner="test-team",
            description="A test application",
        )
        await session.commit()

        assert app.id is not None
        assert app.app_id == "test-app"
        assert app.name == "Test Application"
        assert app.owner == "test-team"
        assert app.is_active is True

    @pytest.mark.asyncio
    async def test_create_application_with_providers(
        self, repo: ApplicationRepository, session: AsyncSession
    ):
        """Test creating an application with custom providers."""
        app = await repo.create(
            app_id="test-app",
            name="Test Application",
            owner="test-team",
            allowed_providers=["openai"],
            allowed_models=["gpt-4o", "gpt-4o-mini"],
        )
        await session.commit()

        assert app.allowed_providers == ["openai"]
        assert "gpt-4o" in app.allowed_models

    @pytest.mark.asyncio
    async def test_get_by_id(self, repo: ApplicationRepository, session: AsyncSession):
        """Test getting an application by ID."""
        app = await repo.create(
            app_id="test-app",
            name="Test Application",
            owner="test-team",
        )
        await session.commit()

        found = await repo.get_by_id(app.id)

        assert found is not None
        assert found.id == app.id

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repo: ApplicationRepository):
        """Test getting a non-existent application by ID."""
        found = await repo.get_by_id(9999)

        assert found is None

    @pytest.mark.asyncio
    async def test_get_by_app_id(self, repo: ApplicationRepository, session: AsyncSession):
        """Test getting an application by app_id."""
        await repo.create(
            app_id="test-app",
            name="Test Application",
            owner="test-team",
        )
        await session.commit()

        found = await repo.get_by_app_id("test-app")

        assert found is not None
        assert found.app_id == "test-app"

    @pytest.mark.asyncio
    async def test_get_by_app_id_not_found(self, repo: ApplicationRepository):
        """Test getting a non-existent application by app_id."""
        found = await repo.get_by_app_id("nonexistent")

        assert found is None

    @pytest.mark.asyncio
    async def test_list_all(self, repo: ApplicationRepository, session: AsyncSession):
        """Test listing all applications."""
        await repo.create(app_id="app1", name="App 1", owner="team1")
        await repo.create(app_id="app2", name="App 2", owner="team2")
        await session.commit()

        apps = await repo.list_all()

        assert len(apps) == 2

    @pytest.mark.asyncio
    async def test_list_all_active_only(self, repo: ApplicationRepository, session: AsyncSession):
        """Test listing active applications only."""
        await repo.create(app_id="app1", name="App 1", owner="team1")
        app2 = await repo.create(app_id="app2", name="App 2", owner="team2")
        app2.is_active = False
        await session.commit()

        apps = await repo.list_all(active_only=True)

        assert len(apps) == 1
        assert apps[0].app_id == "app1"

    @pytest.mark.asyncio
    async def test_list_all_with_pagination(
        self, repo: ApplicationRepository, session: AsyncSession
    ):
        """Test listing applications with pagination."""
        for i in range(5):
            await repo.create(app_id=f"app{i}", name=f"App {i}", owner="team")
        await session.commit()

        apps = await repo.list_all(skip=2, limit=2)

        assert len(apps) == 2

    @pytest.mark.asyncio
    async def test_update_application(self, repo: ApplicationRepository, session: AsyncSession):
        """Test updating an application."""
        await repo.create(
            app_id="test-app",
            name="Test Application",
            owner="test-team",
        )
        await session.commit()

        updated = await repo.update(
            app_id="test-app",
            name="Updated Name",
            description="Updated description",
        )
        await session.commit()

        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.description == "Updated description"

    @pytest.mark.asyncio
    async def test_update_nonexistent_application(self, repo: ApplicationRepository):
        """Test updating a non-existent application."""
        updated = await repo.update(
            app_id="nonexistent",
            name="New Name",
        )

        assert updated is None

    @pytest.mark.asyncio
    async def test_update_partial(self, repo: ApplicationRepository, session: AsyncSession):
        """Test partial update of an application."""
        await repo.create(
            app_id="test-app",
            name="Test Application",
            owner="test-team",
            description="Original description",
        )
        await session.commit()

        updated = await repo.update(
            app_id="test-app",
            name="Updated Name",
        )
        await session.commit()

        assert updated.name == "Updated Name"
        assert updated.description == "Original description"  # Unchanged

    @pytest.mark.asyncio
    async def test_delete_soft(self, repo: ApplicationRepository, session: AsyncSession):
        """Test soft deleting an application."""
        await repo.create(
            app_id="test-app",
            name="Test Application",
            owner="test-team",
        )
        await session.commit()

        result = await repo.delete("test-app")
        await session.commit()

        assert result is True

        app = await repo.get_by_app_id("test-app")
        assert app is not None
        assert app.is_active is False

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, repo: ApplicationRepository):
        """Test deleting a non-existent application."""
        result = await repo.delete("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_hard_delete(self, repo: ApplicationRepository, session: AsyncSession):
        """Test permanently deleting an application."""
        await repo.create(
            app_id="test-app",
            name="Test Application",
            owner="test-team",
        )
        await session.commit()

        result = await repo.hard_delete("test-app")
        await session.commit()

        assert result is True

        app = await repo.get_by_app_id("test-app")
        assert app is None

    @pytest.mark.asyncio
    async def test_hard_delete_nonexistent(self, repo: ApplicationRepository):
        """Test hard deleting a non-existent application."""
        result = await repo.hard_delete("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_get_by_uuid(self, repo: ApplicationRepository, session: AsyncSession):
        """Test getting an application by UUID."""
        app = await repo.create(
            app_id="test-app",
            name="Test Application",
            owner="test-team",
        )
        await session.commit()

        found = await repo.get_by_uuid(app.uuid)

        assert found is not None
        assert found.id == app.id

    @pytest.mark.asyncio
    async def test_default_providers(self, repo: ApplicationRepository, session: AsyncSession):
        """Test default allowed providers."""
        app = await repo.create(
            app_id="test-app",
            name="Test Application",
            owner="test-team",
        )
        await session.commit()

        assert "openai" in app.allowed_providers
        assert "anthropic" in app.allowed_providers
