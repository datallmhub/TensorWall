"""Unit tests for Audit Repository."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta

from backend.db.repositories.audit import AuditRepository
from backend.db.models import AuditLog, AuditEventType


class TestAuditRepositoryLog:
    """Tests for log method."""

    @pytest.mark.asyncio
    async def test_log_basic_event(self):
        """Test logging a basic audit event."""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        repo = AuditRepository(mock_session)
        await repo.log(
            event_type=AuditEventType.REQUEST,
            request_id="req-123",
            app_id="test-app",
        )

        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_with_all_fields(self):
        """Test logging event with all fields."""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        repo = AuditRepository(mock_session)
        await repo.log(
            event_type=AuditEventType.POLICY_DECISION,
            request_id="req-123",
            app_id="test-app",
            feature="chat",
            environment="production",
            owner="team-a",
            model="gpt-4",
            provider="openai",
            policy_decision="deny",
            policy_reason="budget exceeded",
            budget_allowed=False,
            security_issues=["prompt_injection"],
            blocked=True,
            error=None,
            metadata={"custom": "data"},
        )

        mock_session.add.assert_called_once()
        added_log = mock_session.add.call_args[0][0]
        assert added_log.blocked is True
        assert added_log.security_issues == ["prompt_injection"]


class TestAuditRepositoryGet:
    """Tests for get methods."""

    @pytest.mark.asyncio
    async def test_get_by_id_found(self):
        """Test getting audit log by ID when found."""
        mock_session = AsyncMock()
        mock_log = MagicMock(spec=AuditLog)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_log
        mock_session.execute.return_value = mock_result

        repo = AuditRepository(mock_session)
        result = await repo.get_by_id(1)

        assert result == mock_log

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self):
        """Test getting audit log by ID when not found."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = AuditRepository(mock_session)
        result = await repo.get_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_request_id(self):
        """Test getting all logs for a request."""
        mock_session = AsyncMock()
        mock_logs = [MagicMock(spec=AuditLog), MagicMock(spec=AuditLog)]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_logs
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = AuditRepository(mock_session)
        result = await repo.get_by_request_id("req-123")

        assert len(result) == 2


class TestAuditRepositoryList:
    """Tests for list methods."""

    @pytest.mark.asyncio
    async def test_list_by_app(self):
        """Test listing logs for an application."""
        mock_session = AsyncMock()
        mock_logs = [MagicMock(spec=AuditLog)]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_logs
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = AuditRepository(mock_session)
        result = await repo.list_by_app(
            app_id="test-app",
            event_type=AuditEventType.REQUEST,
            from_date=datetime.utcnow() - timedelta(days=1),
            to_date=datetime.utcnow(),
            limit=50,
            offset=0,
        )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_blocked(self):
        """Test listing blocked requests."""
        mock_session = AsyncMock()
        mock_logs = [MagicMock(spec=AuditLog)]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_logs
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = AuditRepository(mock_session)
        result = await repo.list_blocked(
            app_id="test-app",
            from_date=datetime.utcnow() - timedelta(days=1),
            limit=50,
        )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_errors(self):
        """Test listing error events."""
        mock_session = AsyncMock()
        mock_logs = [MagicMock(spec=AuditLog)]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_logs
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = AuditRepository(mock_session)
        result = await repo.list_errors(
            app_id="test-app",
            from_date=datetime.utcnow() - timedelta(hours=6),
            limit=100,
        )

        assert len(result) == 1


class TestAuditRepositoryCount:
    """Tests for count methods."""

    @pytest.mark.asyncio
    async def test_count_by_app(self):
        """Test counting logs for an application."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 42
        mock_session.execute.return_value = mock_result

        repo = AuditRepository(mock_session)
        result = await repo.count_by_app(
            app_id="test-app",
            event_type=AuditEventType.RESPONSE,
            from_date=datetime.utcnow() - timedelta(days=7),
        )

        assert result == 42

    @pytest.mark.asyncio
    async def test_count_errors(self):
        """Test counting error events."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 5
        mock_session.execute.return_value = mock_result

        repo = AuditRepository(mock_session)
        result = await repo.count_errors(
            from_date=datetime.utcnow() - timedelta(hours=24),
        )

        assert result == 5


class TestAuditRepositoryCleanup:
    """Tests for cleanup method."""

    @pytest.mark.asyncio
    async def test_cleanup_old_logs(self):
        """Test cleaning up old logs."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 100
        mock_session.execute.return_value = mock_result
        mock_session.flush = AsyncMock()

        repo = AuditRepository(mock_session)
        result = await repo.cleanup_old_logs(retention_days=30)

        assert result == 100
        mock_session.flush.assert_called_once()
