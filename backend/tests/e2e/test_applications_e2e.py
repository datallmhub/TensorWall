"""E2E tests for Applications API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Application


class TestApplicationsE2E:
    """E2E tests for /admin/applications endpoints."""

    @pytest.mark.asyncio
    async def test_create_application(self, client: AsyncClient, seed_organization):
        """Test creating a new application."""
        response = await client.post(
            "/admin/applications",
            json={
                "app_id": "new-e2e-app",
                "name": "New E2E Application",
                "owner": "e2e-team",
                "description": "Created by E2E test",
                "allowed_providers": ["openai"],
                "allowed_models": ["gpt-4o-mini"],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["app_id"] == "new-e2e-app"
        assert data["name"] == "New E2E Application"
        assert data["is_active"] is True
        assert "uuid" in data

    @pytest.mark.asyncio
    async def test_create_application_duplicate_fails(
        self, client: AsyncClient, seed_application: Application
    ):
        """Test that creating duplicate app_id fails."""
        response = await client.post(
            "/admin/applications",
            json={
                "app_id": seed_application.app_id,  # Same as existing
                "name": "Duplicate App",
                "owner": "test-team",
            },
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_application_invalid_app_id(self, client: AsyncClient):
        """Test that invalid app_id format is rejected."""
        response = await client.post(
            "/admin/applications",
            json={
                "app_id": "INVALID_APP_ID",  # Uppercase and underscore not allowed
                "name": "Invalid App",
                "owner": "test-team",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_applications(self, client: AsyncClient, seed_application: Application):
        """Test listing applications."""
        response = await client.get("/admin/applications")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(app["app_id"] == seed_application.app_id for app in data)

    @pytest.mark.asyncio
    async def test_get_application_by_uuid(
        self, client: AsyncClient, seed_application: Application
    ):
        """Test getting application by UUID."""
        response = await client.get(f"/admin/applications/{seed_application.uuid}")

        assert response.status_code == 200
        data = response.json()
        assert data["app_id"] == seed_application.app_id
        assert data["uuid"] == str(seed_application.uuid)

    @pytest.mark.asyncio
    async def test_get_application_not_found(self, client: AsyncClient):
        """Test getting non-existent application."""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = await client.get(f"/admin/applications/{fake_uuid}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_application(self, client: AsyncClient, seed_application: Application):
        """Test updating an application."""
        response = await client.patch(
            f"/admin/applications/{seed_application.uuid}",
            json={
                "name": "Updated Application Name",
                "description": "Updated description",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Application Name"
        assert data["description"] == "Updated description"

    @pytest.mark.asyncio
    async def test_update_application_allowed_models(
        self, client: AsyncClient, seed_application: Application
    ):
        """Test updating application's allowed models."""
        new_models = ["gpt-4o", "claude-3-opus", "claude-3-sonnet"]
        response = await client.patch(
            f"/admin/applications/{seed_application.uuid}",
            json={"allowed_models": new_models},
        )

        assert response.status_code == 200
        data = response.json()
        assert set(data["allowed_models"]) == set(new_models)

    @pytest.mark.asyncio
    async def test_deactivate_application(self, client: AsyncClient, seed_application: Application):
        """Test deactivating an application."""
        response = await client.patch(
            f"/admin/applications/{seed_application.uuid}",
            json={"is_active": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False

    @pytest.mark.asyncio
    async def test_delete_application(self, client: AsyncClient, db: AsyncSession):
        """Test deleting an application (soft delete)."""
        # Create a new app to delete - using only required fields
        app = Application(
            app_id="app-to-delete",
            name="Delete Me",
            owner="test",
        )
        db.add(app)
        await db.commit()
        await db.refresh(app)

        response = await client.delete(f"/admin/applications/{app.uuid}")

        assert response.status_code == 204

        # Verify it's deactivated (soft delete)
        get_response = await client.get(f"/admin/applications/{app.uuid}")
        # The app may still be accessible but inactive, or may return 404
        assert get_response.status_code in [200, 404]
        if get_response.status_code == 200:
            data = get_response.json()
            assert data.get("is_active") is False


class TestApplicationApiKeysE2E:
    """E2E tests for application API key management."""

    @pytest.mark.asyncio
    async def test_create_api_key(self, client: AsyncClient, seed_application: Application):
        """Test creating an API key for an application."""
        response = await client.post(
            f"/admin/applications/{seed_application.uuid}/keys",
            json={
                "name": "New E2E Key",
                "environment": "production",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New E2E Key"
        assert data["environment"] == "production"
        assert "api_key" in data  # Raw key only on creation
        assert data["api_key"].startswith("gw_")

    @pytest.mark.asyncio
    async def test_list_api_keys(
        self, client: AsyncClient, seed_application: Application, seed_api_key
    ):
        """Test listing API keys for an application."""
        response = await client.get(f"/admin/applications/{seed_application.uuid}/keys")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_revoke_api_key(
        self, client: AsyncClient, seed_application: Application, seed_api_key
    ):
        """Test revoking an API key."""
        api_key, _ = seed_api_key
        response = await client.delete(
            f"/admin/applications/{seed_application.uuid}/keys/{api_key.id}"
        )

        assert response.status_code == 204


class TestApplicationValidationE2E:
    """E2E tests for application validation rules."""

    @pytest.mark.asyncio
    async def test_app_id_min_length(self, client: AsyncClient):
        """Test that app_id must be at least 3 characters."""
        response = await client.post(
            "/admin/applications",
            json={
                "app_id": "ab",  # Too short
                "name": "Short ID App",
                "owner": "test",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_app_id_max_length(self, client: AsyncClient):
        """Test that app_id has maximum length."""
        response = await client.post(
            "/admin/applications",
            json={
                "app_id": "a" * 101,  # Too long
                "name": "Long ID App",
                "owner": "test",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_name_required(self, client: AsyncClient):
        """Test that name is required."""
        response = await client.post(
            "/admin/applications",
            json={
                "app_id": "valid-app-id",
                "owner": "test",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_owner_required(self, client: AsyncClient):
        """Test that owner is required."""
        response = await client.post(
            "/admin/applications",
            json={
                "app_id": "valid-app-id",
                "name": "Valid App",
            },
        )

        assert response.status_code == 422
