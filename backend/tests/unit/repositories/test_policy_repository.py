"""Unit tests for Policy Repository."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from backend.db.repositories.policy import PolicyRepository
from backend.db.models import PolicyRule, PolicyAction


class TestPolicyRepositoryCreate:
    """Tests for creating policies."""

    @pytest.mark.asyncio
    async def test_create_minimal(self):
        """Test creating a policy with minimal fields."""
        mock_session = AsyncMock()
        repo = PolicyRepository(mock_session)

        # Create mock rule
        mock_rule = MagicMock(spec=PolicyRule)
        mock_rule.name = "test-rule"
        mock_rule.conditions = {"key": "value"}
        mock_rule.action = PolicyAction.ALLOW

        with patch.object(repo, "session") as session:
            session.add = MagicMock()
            session.flush = AsyncMock()

            await repo.create(
                name="test-rule",
                conditions={"key": "value"},
            )

            session.add.assert_called_once()
            session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_full(self):
        """Test creating a policy with all fields."""
        mock_session = AsyncMock()
        repo = PolicyRepository(mock_session)

        with patch.object(repo, "session") as session:
            session.add = MagicMock()
            session.flush = AsyncMock()

            await repo.create(
                name="full-rule",
                conditions={"model": "gpt-4"},
                action=PolicyAction.DENY,
                application_id=1,
                user_email="test@example.com",
                description="Test description",
                priority=10,
            )

            session.add.assert_called_once()


class TestPolicyRepositoryGet:
    """Tests for getting policies."""

    @pytest.mark.asyncio
    async def test_get_by_id_found(self):
        """Test getting policy by ID when found."""
        mock_session = AsyncMock()
        mock_rule = MagicMock(spec=PolicyRule)
        mock_rule.id = 1
        mock_rule.name = "test-rule"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_rule
        mock_session.execute.return_value = mock_result

        repo = PolicyRepository(mock_session)
        result = await repo.get_by_id(1)

        assert result == mock_rule

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self):
        """Test getting policy by ID when not found."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = PolicyRepository(mock_session)
        result = await repo.get_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_uuid_found(self):
        """Test getting policy by UUID when found."""
        mock_session = AsyncMock()
        mock_rule = MagicMock(spec=PolicyRule)
        mock_rule.uuid = uuid4()
        mock_rule.name = "test-rule"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_rule
        mock_session.execute.return_value = mock_result

        repo = PolicyRepository(mock_session)
        result = await repo.get_by_uuid(mock_rule.uuid)

        assert result == mock_rule

    @pytest.mark.asyncio
    async def test_get_by_uuid_not_found(self):
        """Test getting policy by UUID when not found."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = PolicyRepository(mock_session)
        result = await repo.get_by_uuid(uuid4())

        assert result is None


class TestPolicyRepositoryList:
    """Tests for listing policies."""

    @pytest.mark.asyncio
    async def test_list_for_application(self):
        """Test listing policies for an application."""
        mock_session = AsyncMock()
        mock_rules = [
            MagicMock(spec=PolicyRule, name="rule-1"),
            MagicMock(spec=PolicyRule, name="rule-2"),
        ]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_rules
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = PolicyRepository(mock_session)
        result = await repo.list_for_application(application_id=1)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_for_application_enabled_only(self):
        """Test listing only enabled policies for an application."""
        mock_session = AsyncMock()
        mock_rules = [MagicMock(spec=PolicyRule)]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_rules
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = PolicyRepository(mock_session)
        result = await repo.list_for_application(application_id=1, enabled_only=True)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_for_application_all(self):
        """Test listing all policies for an application."""
        mock_session = AsyncMock()
        mock_rules = [
            MagicMock(spec=PolicyRule, is_enabled=True),
            MagicMock(spec=PolicyRule, is_enabled=False),
        ]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_rules
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = PolicyRepository(mock_session)
        result = await repo.list_for_application(application_id=1, enabled_only=False)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_global_rules(self):
        """Test listing global rules."""
        mock_session = AsyncMock()
        mock_rules = [MagicMock(spec=PolicyRule, application_id=None)]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_rules
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = PolicyRepository(mock_session)
        result = await repo.list_global_rules()

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_by_application(self):
        """Test listing rules specific to an application."""
        mock_session = AsyncMock()
        mock_rules = [MagicMock(spec=PolicyRule, application_id=1)]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_rules
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = PolicyRepository(mock_session)
        result = await repo.list_by_application(application_id=1)

        assert len(result) == 1


class TestPolicyRepositoryUpdate:
    """Tests for updating policies."""

    @pytest.mark.asyncio
    async def test_update_found(self):
        """Test updating a policy when found."""
        mock_session = AsyncMock()
        mock_rule = MagicMock(spec=PolicyRule)
        mock_rule.id = 1
        mock_rule.name = "old-name"
        mock_rule.description = None
        mock_rule.conditions = {}
        mock_rule.action = PolicyAction.ALLOW
        mock_rule.priority = 0
        mock_rule.is_enabled = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_rule
        mock_session.execute.return_value = mock_result
        mock_session.flush = AsyncMock()

        repo = PolicyRepository(mock_session)
        result = await repo.update(
            id=1,
            name="new-name",
            description="New description",
            priority=5,
        )

        assert result == mock_rule
        assert mock_rule.name == "new-name"
        assert mock_rule.description == "New description"
        assert mock_rule.priority == 5

    @pytest.mark.asyncio
    async def test_update_not_found(self):
        """Test updating a policy when not found."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = PolicyRepository(mock_session)
        result = await repo.update(id=999, name="new-name")

        assert result is None

    @pytest.mark.asyncio
    async def test_update_all_fields(self):
        """Test updating all fields of a policy."""
        mock_session = AsyncMock()
        mock_rule = MagicMock(spec=PolicyRule)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_rule
        mock_session.execute.return_value = mock_result
        mock_session.flush = AsyncMock()

        repo = PolicyRepository(mock_session)
        result = await repo.update(
            id=1,
            name="updated-name",
            description="Updated description",
            conditions={"new": "condition"},
            action=PolicyAction.DENY,
            priority=10,
            is_enabled=False,
        )

        assert result == mock_rule


class TestPolicyRepositoryDelete:
    """Tests for deleting policies."""

    @pytest.mark.asyncio
    async def test_delete_found(self):
        """Test deleting a policy when found."""
        mock_session = AsyncMock()
        mock_rule = MagicMock(spec=PolicyRule)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_rule
        mock_session.execute.return_value = mock_result
        mock_session.delete = AsyncMock()
        mock_session.flush = AsyncMock()

        repo = PolicyRepository(mock_session)
        result = await repo.delete(id=1)

        assert result is True
        mock_session.delete.assert_called_once_with(mock_rule)

    @pytest.mark.asyncio
    async def test_delete_not_found(self):
        """Test deleting a policy when not found."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = PolicyRepository(mock_session)
        result = await repo.delete(id=999)

        assert result is False


class TestPolicyRepositoryEnableDisable:
    """Tests for enabling/disabling policies."""

    @pytest.mark.asyncio
    async def test_enable_found(self):
        """Test enabling a policy when found."""
        mock_session = AsyncMock()
        mock_rule = MagicMock(spec=PolicyRule)
        mock_rule.is_enabled = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_rule
        mock_session.execute.return_value = mock_result
        mock_session.flush = AsyncMock()

        repo = PolicyRepository(mock_session)
        result = await repo.enable(id=1)

        assert result is True
        assert mock_rule.is_enabled is True

    @pytest.mark.asyncio
    async def test_enable_not_found(self):
        """Test enabling a policy when not found."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = PolicyRepository(mock_session)
        result = await repo.enable(id=999)

        assert result is False

    @pytest.mark.asyncio
    async def test_disable_found(self):
        """Test disabling a policy when found."""
        mock_session = AsyncMock()
        mock_rule = MagicMock(spec=PolicyRule)
        mock_rule.is_enabled = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_rule
        mock_session.execute.return_value = mock_result
        mock_session.flush = AsyncMock()

        repo = PolicyRepository(mock_session)
        result = await repo.disable(id=1)

        assert result is True
        assert mock_rule.is_enabled is False

    @pytest.mark.asyncio
    async def test_disable_not_found(self):
        """Test disabling a policy when not found."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = PolicyRepository(mock_session)
        result = await repo.disable(id=999)

        assert result is False
