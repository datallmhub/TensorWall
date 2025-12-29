"""E2E tests for Policies API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Application, PolicyRule, PolicyAction


class TestPoliciesE2E:
    """E2E tests for /admin/policies endpoints."""

    @pytest.mark.asyncio
    async def test_create_policy(self, client: AsyncClient, seed_application: Application):
        """Test creating a new policy."""
        response = await client.post(
            "/admin/policies",
            json={
                "name": "new-e2e-policy",
                "description": "E2E test policy",
                "app_id": seed_application.app_id,
                "conditions": {
                    "environments": ["production"],
                    "models": ["gpt-4o"],
                    "max_tokens": 2000,
                },
                "action": "deny",
                "priority": 20,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "new-e2e-policy"
        assert data["action"] == "deny"
        assert data["priority"] == 20
        assert data["is_enabled"] is True

    @pytest.mark.asyncio
    async def test_create_global_policy(self, client: AsyncClient):
        """Test creating a global policy (no app_id)."""
        response = await client.post(
            "/admin/policies",
            json={
                "name": "global-policy",
                "description": "Applies to all apps",
                "conditions": {"max_tokens": 8000},
                "action": "warn",
                "priority": 5,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["app_id"] is None
        assert data["action"] == "warn"

    @pytest.mark.asyncio
    async def test_list_policies(self, client: AsyncClient, seed_policy: PolicyRule):
        """Test listing policies."""
        response = await client.get("/admin/policies")

        assert response.status_code == 200
        data = response.json()
        # Response is paginated with page/page_size/total format
        assert "items" in data
        assert "page" in data
        assert "total" in data
        items = data["items"]
        assert isinstance(items, list)
        assert len(items) >= 1

    @pytest.mark.asyncio
    async def test_list_policies_by_app(
        self, client: AsyncClient, seed_application: Application, seed_policy: PolicyRule
    ):
        """Test listing policies filtered by app."""
        response = await client.get(f"/admin/policies?app_id={seed_application.app_id}")

        assert response.status_code == 200
        data = response.json()
        # Response is paginated
        items = data["items"]
        assert all(p["app_id"] == seed_application.app_id or p["app_id"] is None for p in items)

    @pytest.mark.asyncio
    async def test_get_policy(self, client: AsyncClient, seed_policy: PolicyRule):
        """Test getting a policy by UUID."""
        response = await client.get(f"/admin/policies/{seed_policy.uuid}")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == seed_policy.name

    @pytest.mark.asyncio
    async def test_get_policy_not_found(self, client: AsyncClient):
        """Test getting non-existent policy."""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = await client.get(f"/admin/policies/{fake_uuid}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_policy(self, client: AsyncClient, seed_policy: PolicyRule):
        """Test updating a policy."""
        response = await client.patch(
            f"/admin/policies/{seed_policy.uuid}",
            json={
                "name": "updated-policy-name",
                "priority": 50,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "updated-policy-name"
        assert data["priority"] == 50

    @pytest.mark.asyncio
    async def test_update_policy_conditions(self, client: AsyncClient, seed_policy: PolicyRule):
        """Test updating policy conditions."""
        new_conditions = {
            "environments": ["staging", "production"],
            "models": ["gpt-4o", "claude-3-opus"],
            "max_tokens": 6000,
        }
        response = await client.patch(
            f"/admin/policies/{seed_policy.uuid}",
            json={"conditions": new_conditions},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["conditions"]["max_tokens"] == 6000
        assert "staging" in data["conditions"]["environments"]

    @pytest.mark.asyncio
    async def test_update_policy_action(self, client: AsyncClient, seed_policy: PolicyRule):
        """Test changing policy action from deny to warn."""
        response = await client.patch(
            f"/admin/policies/{seed_policy.uuid}",
            json={"action": "warn"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "warn"

    @pytest.mark.asyncio
    async def test_disable_policy(self, client: AsyncClient, seed_policy: PolicyRule):
        """Test disabling a policy."""
        response = await client.patch(
            f"/admin/policies/{seed_policy.uuid}",
            json={"is_enabled": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_enabled"] is False

    @pytest.mark.asyncio
    async def test_delete_policy(self, client: AsyncClient, db: AsyncSession, seed_application):
        """Test deleting a policy."""
        # Create a policy to delete
        policy = PolicyRule(
            name="policy-to-delete",
            application_id=seed_application.id,
            conditions={},
            action=PolicyAction.ALLOW,
            priority=1,
        )
        db.add(policy)
        await db.commit()
        await db.refresh(policy)

        response = await client.delete(f"/admin/policies/{policy.uuid}")

        assert response.status_code in [200, 204]


class TestPolicyConditionsE2E:
    """E2E tests for policy condition types."""

    @pytest.mark.asyncio
    async def test_policy_with_environment_condition(
        self, client: AsyncClient, seed_application: Application
    ):
        """Test policy with environment restrictions."""
        response = await client.post(
            "/admin/policies",
            json={
                "name": "env-policy",
                "app_id": seed_application.app_id,
                "conditions": {
                    "environments": ["production"],
                },
                "action": "deny",
                "priority": 10,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["conditions"]["environments"] == ["production"]

    @pytest.mark.asyncio
    async def test_policy_with_model_condition(
        self, client: AsyncClient, seed_application: Application
    ):
        """Test policy with model restrictions."""
        response = await client.post(
            "/admin/policies",
            json={
                "name": "model-policy",
                "app_id": seed_application.app_id,
                "conditions": {
                    "models": ["gpt-4o", "gpt-4o-mini"],
                    "blocked_models": ["claude-*"],
                },
                "action": "deny",
                "priority": 15,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "gpt-4o" in data["conditions"]["models"]

    @pytest.mark.asyncio
    async def test_policy_with_token_limit(
        self, client: AsyncClient, seed_application: Application
    ):
        """Test policy with token limits."""
        response = await client.post(
            "/admin/policies",
            json={
                "name": "token-policy",
                "app_id": seed_application.app_id,
                "conditions": {
                    "max_tokens": 4000,
                    "max_context_tokens": 128000,
                },
                "action": "deny",
                "priority": 25,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["conditions"]["max_tokens"] == 4000

    @pytest.mark.asyncio
    async def test_policy_with_time_restriction(
        self, client: AsyncClient, seed_application: Application
    ):
        """Test policy with time-based restrictions."""
        response = await client.post(
            "/admin/policies",
            json={
                "name": "time-policy",
                "app_id": seed_application.app_id,
                "conditions": {
                    "allowed_hours": [9, 17],  # 9 AM to 5 PM
                },
                "action": "deny",
                "priority": 30,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["conditions"]["allowed_hours"] == [9, 17]


class TestPolicyPriorityE2E:
    """E2E tests for policy priority ordering."""

    @pytest.mark.asyncio
    async def test_policies_ordered_by_priority(
        self, client: AsyncClient, seed_application: Application
    ):
        """Test that policies are returned ordered by priority (desc)."""
        # Create multiple policies with different priorities
        for priority in [5, 20, 10, 15]:
            await client.post(
                "/admin/policies",
                json={
                    "name": f"priority-{priority}-policy",
                    "app_id": seed_application.app_id,
                    "conditions": {},
                    "action": "allow",
                    "priority": priority,
                },
            )

        response = await client.get(f"/admin/policies?app_id={seed_application.app_id}")

        assert response.status_code == 200
        data = response.json()
        items = data["items"]

        # Verify descending order
        priorities = [p["priority"] for p in items]
        assert priorities == sorted(priorities, reverse=True)
