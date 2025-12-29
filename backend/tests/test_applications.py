"""Tests for application management endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_application(client: AsyncClient, sample_application_data):
    """Test creating a new application."""
    response = await client.post("/admin/applications", json=sample_application_data)

    assert response.status_code == 201
    data = response.json()
    assert data["app_id"] == sample_application_data["app_id"]
    assert data["name"] == sample_application_data["name"]
    assert data["owner"] == sample_application_data["owner"]
    assert data["is_active"] is True
    assert "uuid" in data  # UUID is returned


@pytest.mark.asyncio
async def test_create_application_duplicate(client: AsyncClient, sample_application_data):
    """Test creating a duplicate application fails."""
    # Create first
    await client.post("/admin/applications", json=sample_application_data)

    # Try to create duplicate
    response = await client.post("/admin/applications", json=sample_application_data)

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_application_invalid_app_id(client: AsyncClient):
    """Test creating an application with invalid app_id fails."""
    data = {
        "app_id": "Invalid App ID!",  # Contains spaces and special chars
        "name": "Test",
        "owner": "test-team",
    }
    response = await client.post("/admin/applications", json=data)

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_list_applications(client: AsyncClient, sample_application_data):
    """Test listing applications."""
    # Create an application
    await client.post("/admin/applications", json=sample_application_data)

    response = await client.get("/admin/applications")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["app_id"] == sample_application_data["app_id"]


@pytest.mark.asyncio
async def test_get_application(client: AsyncClient, sample_application_data):
    """Test getting a specific application by UUID."""
    # Create an application
    create_response = await client.post("/admin/applications", json=sample_application_data)
    app_uuid = create_response.json()["uuid"]

    # Get by UUID
    response = await client.get(f"/admin/applications/{app_uuid}")

    assert response.status_code == 200
    data = response.json()
    assert data["app_id"] == sample_application_data["app_id"]
    assert data["uuid"] == app_uuid


@pytest.mark.asyncio
async def test_get_application_not_found(client: AsyncClient):
    """Test getting a non-existent application."""
    # Use a valid UUID format that doesn't exist
    fake_uuid = "00000000-0000-0000-0000-000000000000"
    response = await client.get(f"/admin/applications/{fake_uuid}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_application(client: AsyncClient, sample_application_data):
    """Test updating an application."""
    # Create an application
    create_response = await client.post("/admin/applications", json=sample_application_data)
    app_uuid = create_response.json()["uuid"]

    # Update it
    update_data = {"name": "Updated Name", "owner": "new-team"}
    response = await client.patch(
        f"/admin/applications/{app_uuid}",
        json=update_data,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["owner"] == "new-team"


@pytest.mark.asyncio
async def test_delete_application_soft(client: AsyncClient, sample_application_data):
    """Test soft deleting an application."""
    # Create an application
    create_response = await client.post("/admin/applications", json=sample_application_data)
    app_uuid = create_response.json()["uuid"]

    # Delete it (soft)
    response = await client.delete(f"/admin/applications/{app_uuid}")

    assert response.status_code == 204

    # It should still exist but be inactive
    response = await client.get(f"/admin/applications/{app_uuid}")
    assert response.status_code == 200
    assert response.json()["is_active"] is False


@pytest.mark.asyncio
async def test_create_api_key(client: AsyncClient, sample_application_data):
    """Test creating an API key for an application."""
    # Create an application
    create_response = await client.post("/admin/applications", json=sample_application_data)
    app_uuid = create_response.json()["uuid"]

    # Create an API key
    key_data = {"name": "Test Key", "environment": "development"}
    response = await client.post(
        f"/admin/applications/{app_uuid}/keys",
        json=key_data,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Key"
    assert data["environment"] == "development"
    assert "api_key" in data  # Raw key returned on creation
    assert data["api_key"].startswith("gw_")


@pytest.mark.asyncio
async def test_list_api_keys(client: AsyncClient, sample_application_data):
    """Test listing API keys for an application."""
    # Create an application
    create_response = await client.post("/admin/applications", json=sample_application_data)
    app_uuid = create_response.json()["uuid"]

    # Create an API key
    key_data = {"name": "Test Key", "environment": "development"}
    await client.post(
        f"/admin/applications/{app_uuid}/keys",
        json=key_data,
    )

    # List keys
    response = await client.get(f"/admin/applications/{app_uuid}/keys")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Test Key"
    assert "api_key" not in data[0]  # Raw key not returned on list


@pytest.mark.asyncio
async def test_revoke_api_key(client: AsyncClient, sample_application_data):
    """Test revoking an API key."""
    # Create an application
    create_response = await client.post("/admin/applications", json=sample_application_data)
    app_uuid = create_response.json()["uuid"]

    # Create an API key
    key_data = {"name": "Test Key", "environment": "development"}
    key_response = await client.post(
        f"/admin/applications/{app_uuid}/keys",
        json=key_data,
    )
    key_id = key_response.json()["id"]

    # Revoke it
    response = await client.delete(f"/admin/applications/{app_uuid}/keys/{key_id}")

    assert response.status_code == 204

    # List should show no active keys
    list_response = await client.get(f"/admin/applications/{app_uuid}/keys")
    assert len(list_response.json()) == 0


@pytest.mark.asyncio
async def test_rotate_api_key(client: AsyncClient, sample_application_data):
    """Test rotating an API key."""
    # Create an application
    create_response = await client.post("/admin/applications", json=sample_application_data)
    app_uuid = create_response.json()["uuid"]

    # Create an API key
    key_data = {"name": "Test Key", "environment": "development"}
    key_response = await client.post(
        f"/admin/applications/{app_uuid}/keys",
        json=key_data,
    )
    old_key_id = key_response.json()["id"]
    old_api_key = key_response.json()["api_key"]

    # Rotate it
    response = await client.post(f"/admin/applications/{app_uuid}/keys/{old_key_id}/rotate")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] != old_key_id
    assert data["api_key"] != old_api_key
    assert "rotated" in data["name"]
