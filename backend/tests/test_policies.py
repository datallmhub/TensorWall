"""Tests for policy management endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_global_policy(client: AsyncClient, sample_policy_data):
    """Test creating a global policy."""
    response = await client.post("/admin/policies", json=sample_policy_data)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == sample_policy_data["name"]
    assert data["app_id"] is None  # Global policy
    assert data["action"] == "deny"
    assert data["is_enabled"] is True
    assert "uuid" in data  # UUID is returned


@pytest.mark.asyncio
async def test_create_app_specific_policy(
    client: AsyncClient, sample_application_data, sample_policy_data
):
    """Test creating an app-specific policy."""
    # Create application first
    await client.post("/admin/applications", json=sample_application_data)

    # Create policy for this app
    sample_policy_data["app_id"] = sample_application_data["app_id"]
    response = await client.post("/admin/policies", json=sample_policy_data)

    assert response.status_code == 201
    data = response.json()
    assert data["app_id"] == sample_application_data["app_id"]


@pytest.mark.asyncio
async def test_create_policy_invalid_action(client: AsyncClient, sample_policy_data):
    """Test creating a policy with invalid action fails."""
    sample_policy_data["action"] = "invalid"
    response = await client.post("/admin/policies", json=sample_policy_data)

    assert response.status_code == 400
    assert "Invalid action" in response.json()["detail"]


@pytest.mark.asyncio
async def test_list_global_policies(client: AsyncClient, sample_policy_data):
    """Test listing global policies (paginated)."""
    # Create a global policy
    await client.post("/admin/policies", json=sample_policy_data)

    # List policies without app_id filter (returns all including global)
    response = await client.get("/admin/policies")

    assert response.status_code == 200
    data = response.json()
    # Paginated response has 'items' key
    assert "items" in data
    assert len(data["items"]) >= 1
    # Find our policy
    found = any(p["name"] == sample_policy_data["name"] for p in data["items"])
    assert found, "Created policy not found in list"


@pytest.mark.asyncio
async def test_get_policy(client: AsyncClient, sample_policy_data):
    """Test getting a specific policy by UUID."""
    create_response = await client.post("/admin/policies", json=sample_policy_data)
    policy_uuid = create_response.json()["uuid"]

    response = await client.get(f"/admin/policies/{policy_uuid}")

    assert response.status_code == 200
    assert response.json()["name"] == sample_policy_data["name"]


@pytest.mark.asyncio
async def test_update_policy(client: AsyncClient, sample_policy_data):
    """Test updating a policy by UUID."""
    create_response = await client.post("/admin/policies", json=sample_policy_data)
    policy_uuid = create_response.json()["uuid"]

    update_data = {
        "name": "Updated Policy",
        "action": "warn",
        "priority": 20,
    }
    response = await client.patch(f"/admin/policies/{policy_uuid}", json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Policy"
    assert data["action"] == "warn"
    assert data["priority"] == 20


@pytest.mark.asyncio
async def test_delete_policy(client: AsyncClient, sample_policy_data):
    """Test deleting a policy by UUID."""
    create_response = await client.post("/admin/policies", json=sample_policy_data)
    policy_uuid = create_response.json()["uuid"]

    response = await client.delete(f"/admin/policies/{policy_uuid}")

    assert response.status_code == 204

    # Verify it's deleted
    get_response = await client.get(f"/admin/policies/{policy_uuid}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_enable_disable_policy(client: AsyncClient, sample_policy_data):
    """Test enabling and disabling a policy by UUID."""
    create_response = await client.post("/admin/policies", json=sample_policy_data)
    policy_uuid = create_response.json()["uuid"]

    # Disable
    disable_response = await client.post(f"/admin/policies/{policy_uuid}/disable")
    assert disable_response.status_code == 200
    assert disable_response.json()["is_enabled"] is False

    # Enable
    enable_response = await client.post(f"/admin/policies/{policy_uuid}/enable")
    assert enable_response.status_code == 200
    assert enable_response.json()["is_enabled"] is True


@pytest.mark.asyncio
async def test_policy_conditions(client: AsyncClient):
    """Test creating a policy with various conditions."""
    policy_data = {
        "name": "complex-policy",
        "conditions": {
            "environments": ["production", "staging"],
            "features": ["chat", "summarize"],
            "models": ["gpt-4o", "gpt-4o-mini"],
            "max_tokens": 8000,
            "max_context_tokens": 128000,
            "allowed_hours": [9, 18],
        },
        "action": "allow",
        "priority": 5,
    }

    response = await client.post("/admin/policies", json=policy_data)

    assert response.status_code == 201
    data = response.json()
    assert data["conditions"]["environments"] == ["production", "staging"]
    assert data["conditions"]["max_tokens"] == 8000
    assert data["conditions"]["allowed_hours"] == [9, 18]
