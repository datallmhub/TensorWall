"""Unit tests for Usage Repository."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta

from backend.db.repositories.usage import UsageRepository
from backend.db.models import UsageRecord, Environment


class TestUsageRepositoryRecord:
    """Tests for record method."""

    @pytest.mark.asyncio
    async def test_record_usage(self):
        """Test recording a usage event."""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        repo = UsageRepository(mock_session)
        await repo.record(
            request_id="req-123",
            app_id="test-app",
            environment=Environment.PRODUCTION,
            provider="openai",
            model="gpt-4",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.015,
            latency_ms=500,
            feature="chat",
        )

        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()


class TestUsageRepositoryGet:
    """Tests for get methods."""

    @pytest.mark.asyncio
    async def test_get_by_request_id_found(self):
        """Test getting usage by request ID when found."""
        mock_session = AsyncMock()
        mock_usage = MagicMock(spec=UsageRecord)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_usage
        mock_session.execute.return_value = mock_result

        repo = UsageRepository(mock_session)
        result = await repo.get_by_request_id("req-123")

        assert result == mock_usage

    @pytest.mark.asyncio
    async def test_get_by_request_id_not_found(self):
        """Test getting usage by request ID when not found."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = UsageRepository(mock_session)
        result = await repo.get_by_request_id("nonexistent")

        assert result is None


class TestUsageRepositoryList:
    """Tests for list methods."""

    @pytest.mark.asyncio
    async def test_list_by_app(self):
        """Test listing usage for an application."""
        mock_session = AsyncMock()
        mock_records = [MagicMock(spec=UsageRecord), MagicMock(spec=UsageRecord)]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_records
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = UsageRepository(mock_session)
        result = await repo.list_by_app(
            app_id="test-app",
            from_date=datetime.utcnow() - timedelta(days=7),
            to_date=datetime.utcnow(),
            limit=50,
            offset=0,
        )

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_all(self):
        """Test listing all usage records."""
        mock_session = AsyncMock()
        mock_records = [MagicMock(spec=UsageRecord)]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_records
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = UsageRepository(mock_session)
        result = await repo.list_all(
            from_date=datetime.utcnow() - timedelta(hours=24),
            to_date=datetime.utcnow(),
            limit=1000,
        )

        assert len(result) == 1


class TestUsageRepositoryAggregations:
    """Tests for aggregation methods."""

    @pytest.mark.asyncio
    async def test_get_total_cost(self):
        """Test getting total cost."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 150.50
        mock_session.execute.return_value = mock_result

        repo = UsageRepository(mock_session)
        result = await repo.get_total_cost(
            app_id="test-app",
            from_date=datetime.utcnow() - timedelta(days=30),
            to_date=datetime.utcnow(),
            feature="chat",
            environment=Environment.PRODUCTION,
        )

        assert result == 150.50

    @pytest.mark.asyncio
    async def test_get_total_tokens(self):
        """Test getting total tokens."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.input_tokens = 10000
        mock_row.output_tokens = 5000
        mock_result.one.return_value = mock_row
        mock_session.execute.return_value = mock_result

        repo = UsageRepository(mock_session)
        result = await repo.get_total_tokens(
            app_id="test-app",
            from_date=datetime.utcnow() - timedelta(days=7),
        )

        assert result["input_tokens"] == 10000
        assert result["output_tokens"] == 5000
        assert result["total_tokens"] == 15000


class TestUsageRepositoryStats:
    """Tests for stats methods."""

    @pytest.mark.asyncio
    async def test_get_stats_by_model(self):
        """Test getting stats grouped by model."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.model = "gpt-4"
        mock_row.request_count = 100
        mock_row.input_tokens = 50000
        mock_row.output_tokens = 25000
        mock_row.total_cost = 75.50
        mock_row.avg_latency_ms = 350.0
        mock_result.all.return_value = [mock_row]
        mock_session.execute.return_value = mock_result

        repo = UsageRepository(mock_session)
        result = await repo.get_stats_by_model(
            app_id="test-app",
            from_date=datetime.utcnow() - timedelta(days=30),
        )

        assert len(result) == 1
        assert result[0]["model"] == "gpt-4"
        assert result[0]["request_count"] == 100
        assert result[0]["total_cost"] == 75.50

    @pytest.mark.asyncio
    async def test_get_stats_by_feature(self):
        """Test getting stats grouped by feature."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.feature = "chat"
        mock_row.request_count = 200
        mock_row.total_cost = 100.00
        mock_row.avg_latency_ms = 400.0
        mock_result.all.return_value = [mock_row]
        mock_session.execute.return_value = mock_result

        repo = UsageRepository(mock_session)
        result = await repo.get_stats_by_feature(
            app_id="test-app",
            from_date=datetime.utcnow() - timedelta(days=7),
        )

        assert len(result) == 1
        assert result[0]["feature"] == "chat"

    @pytest.mark.asyncio
    async def test_get_daily_stats(self):
        """Test getting daily stats."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.date = datetime.utcnow().date()
        mock_row.request_count = 50
        mock_row.total_cost = 25.00
        mock_row.input_tokens = 10000
        mock_row.output_tokens = 5000
        mock_result.all.return_value = [mock_row]
        mock_session.execute.return_value = mock_result

        repo = UsageRepository(mock_session)
        result = await repo.get_daily_stats(app_id="test-app", days=7)

        assert len(result) == 1
        assert result[0]["request_count"] == 50
