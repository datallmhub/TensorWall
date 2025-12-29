"""Tests for health endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Test the health endpoint returns ok."""
    response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


@pytest.mark.asyncio
async def test_liveness_endpoint(client: AsyncClient):
    """Test the liveness endpoint returns alive."""
    response = await client.get("/health/live")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"


@pytest.mark.asyncio
async def test_ready_endpoint(client: AsyncClient):
    """Test the readiness endpoint.

    Note: This endpoint checks DB and Redis connectivity.
    In test environment with the test DB but no Redis,
    it may return 503 (not ready) which is expected behavior.
    We accept both 200 (all healthy) and 503 (some unhealthy).
    """
    response = await client.get("/ready")

    # Accept both 200 (ready) and 503 (not ready due to Redis)
    assert response.status_code in (200, 503)
    data = response.json()
    assert data["status"] in ("ready", "not_ready")
    assert "checks" in data
    assert "database" in data["checks"]
    assert "redis" in data["checks"]
