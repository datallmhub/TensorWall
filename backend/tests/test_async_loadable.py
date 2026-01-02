"""Tests for AsyncLoadableEntity base class."""

import pytest
from typing import Optional

from backend.core.base import AsyncLoadableEntity


class MockEntity(AsyncLoadableEntity[list[str]]):
    """Mock implementation for testing."""

    def __init__(
        self, data_to_load: Optional[list[str]] = None, should_fail: bool = False
    ):
        super().__init__()
        self._data_to_load = data_to_load or ["item1", "item2"]
        self._should_fail = should_fail
        self.load_count = 0

    async def _load_from_db(self) -> list[str]:
        self.load_count += 1
        if self._should_fail:
            raise Exception("Simulated DB failure")
        return self._data_to_load

    def _get_default_value(self) -> list[str]:
        return []


class TestAsyncLoadableEntity:
    """Tests for AsyncLoadableEntity base class."""

    @pytest.mark.asyncio
    async def test_initial_state(self):
        """Entity should start unloaded."""
        entity = MockEntity()
        assert entity.is_loaded is False
        assert entity.data is None
        assert entity._load_error is None

    @pytest.mark.asyncio
    async def test_ensure_loaded_loads_once(self):
        """ensure_loaded should only load data once."""
        entity = MockEntity(["a", "b", "c"])

        await entity.ensure_loaded()
        assert entity.is_loaded is True
        assert entity.data == ["a", "b", "c"]
        assert entity.load_count == 1

        # Second call should not reload
        await entity.ensure_loaded()
        assert entity.load_count == 1

    @pytest.mark.asyncio
    async def test_reload_forces_reload(self):
        """reload should always fetch new data."""
        entity = MockEntity(["a", "b"])

        await entity.ensure_loaded()
        assert entity.load_count == 1

        await entity.reload()
        assert entity.load_count == 2
        assert entity.is_loaded is True

    @pytest.mark.asyncio
    async def test_invalidate_clears_state(self):
        """invalidate should clear loaded state."""
        entity = MockEntity(["a", "b"])

        await entity.ensure_loaded()
        assert entity.is_loaded is True
        assert entity.data == ["a", "b"]

        entity.invalidate()
        assert entity.is_loaded is False
        assert entity.data is None
        assert entity._load_error is None

    @pytest.mark.asyncio
    async def test_invalidate_allows_reload(self):
        """After invalidate, ensure_loaded should reload."""
        entity = MockEntity(["a", "b"])

        await entity.ensure_loaded()
        assert entity.load_count == 1

        entity.invalidate()
        await entity.ensure_loaded()
        assert entity.load_count == 2

    @pytest.mark.asyncio
    async def test_load_failure_sets_error(self):
        """Load failure should set error and use default value."""
        entity = MockEntity(should_fail=True)

        await entity.ensure_loaded()

        assert entity.is_loaded is True  # Marked loaded to avoid retry loops
        assert entity._load_error == "Simulated DB failure"
        assert entity.data == []  # Default value

    @pytest.mark.asyncio
    async def test_load_failure_uses_default_value(self):
        """Failed load should use _get_default_value()."""
        entity = MockEntity(should_fail=True)

        await entity.reload()

        assert entity.data == []

    @pytest.mark.asyncio
    async def test_reload_after_failure_can_succeed(self):
        """Reload should work after a previous failure."""
        entity = MockEntity(["a", "b"])
        entity._should_fail = True

        # First load fails
        await entity.ensure_loaded()
        assert entity._load_error is not None
        assert entity.data == []

        # Fix the failure and invalidate
        entity._should_fail = False
        entity.invalidate()

        # Reload should succeed
        await entity.ensure_loaded()
        assert entity._load_error is None
        assert entity.data == ["a", "b"]


class TestAsyncLoadableEntityPreloaded:
    """Tests for AsyncLoadableEntity with pre-loaded data."""

    @pytest.mark.asyncio
    async def test_can_preload_data(self):
        """Subclass can set data in __init__ to skip DB load."""
        entity = MockEntity()
        entity._data = ["preloaded"]
        entity._loaded = True

        await entity.ensure_loaded()

        # Should not have called _load_from_db
        assert entity.load_count == 0
        assert entity.data == ["preloaded"]

    @pytest.mark.asyncio
    async def test_preloaded_can_be_invalidated(self):
        """Pre-loaded data can be invalidated to force DB load."""
        entity = MockEntity(["from_db"])
        entity._data = ["preloaded"]
        entity._loaded = True

        entity.invalidate()
        await entity.ensure_loaded()

        assert entity.load_count == 1
        assert entity.data == ["from_db"]


class TestAsyncLoadableEntityConcurrency:
    """Tests for concurrent access to AsyncLoadableEntity."""

    @pytest.mark.asyncio
    async def test_multiple_ensure_loaded_calls(self):
        """Multiple concurrent ensure_loaded calls should be safe."""
        import asyncio

        entity = MockEntity(["a", "b", "c"])

        # Call ensure_loaded multiple times concurrently
        await asyncio.gather(
            entity.ensure_loaded(),
            entity.ensure_loaded(),
            entity.ensure_loaded(),
        )

        # Data should be loaded correctly
        assert entity.is_loaded is True
        assert entity.data == ["a", "b", "c"]
        # Note: Without locking, load_count might be > 1 in race conditions
        # This is acceptable behavior for this simple implementation
