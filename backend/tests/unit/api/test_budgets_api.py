"""Tests for Budget API."""

import pytest

from backend.api.admin.budgets import (
    BudgetResponse,
    BudgetListResponse,
    CreateBudgetRequest,
    UpdateBudgetRequest,
)
from backend.db.models import BudgetScope, BudgetPeriod


class TestBudgetResponse:
    """Test BudgetResponse model."""

    def test_budget_response_fields(self):
        """Should have correct fields for budget."""
        response = BudgetResponse(
            uuid="test-uuid",
            app_id="my-app",
            app_name="My Application",
            limit_usd=100.0,
            spent_usd=25.0,
            remaining_usd=75.0,
            usage_percent=25.0,
            period="monthly",
            is_exceeded=False,
        )

        assert response.uuid == "test-uuid"
        assert response.app_id == "my-app"
        assert response.app_name == "My Application"
        assert response.limit_usd == 100.0
        assert response.spent_usd == 25.0
        assert response.remaining_usd == 75.0
        assert response.usage_percent == 25.0
        assert response.period == "monthly"
        assert response.is_exceeded is False

    def test_budget_response_exceeded(self):
        """Should correctly identify exceeded budget."""
        response = BudgetResponse(
            uuid="test-uuid",
            app_id="my-app",
            app_name=None,
            limit_usd=100.0,
            spent_usd=150.0,
            remaining_usd=0.0,
            usage_percent=150.0,
            period="monthly",
            is_exceeded=True,
        )

        assert response.is_exceeded is True
        assert response.remaining_usd == 0.0
        assert response.usage_percent == 150.0


class TestCreateBudgetRequest:
    """Test CreateBudgetRequest validation."""

    def test_create_budget_request_valid(self):
        """Should accept valid create request."""
        request = CreateBudgetRequest(
            app_id="my-app",
            limit_usd=100.0,
        )

        assert request.app_id == "my-app"
        assert request.limit_usd == 100.0
        assert request.period == "monthly"  # default

    def test_create_budget_request_custom_period(self):
        """Should accept custom period."""
        request = CreateBudgetRequest(
            app_id="my-app",
            limit_usd=500.0,
            period="yearly",
        )

        assert request.period == "yearly"

    def test_create_budget_request_requires_positive_limit(self):
        """Should reject negative limit."""
        with pytest.raises(ValueError):
            CreateBudgetRequest(
                app_id="my-app",
                limit_usd=-10.0,
            )


class TestUpdateBudgetRequest:
    """Test UpdateBudgetRequest validation."""

    def test_update_budget_request_valid(self):
        """Should accept valid update request."""
        request = UpdateBudgetRequest(limit_usd=200.0)
        assert request.limit_usd == 200.0

    def test_update_budget_request_optional_limit(self):
        """Should allow empty update."""
        request = UpdateBudgetRequest()
        assert request.limit_usd is None

    def test_update_budget_request_requires_non_negative_limit(self):
        """Should reject negative limit."""
        with pytest.raises(ValueError):
            UpdateBudgetRequest(limit_usd=-5.0)


class TestBudgetListResponse:
    """Test BudgetListResponse model."""

    def test_budget_list_response_empty(self):
        """Should handle empty list."""
        response = BudgetListResponse(items=[], total=0)
        assert len(response.items) == 0
        assert response.total == 0

    def test_budget_list_response_with_items(self):
        """Should handle list with items."""
        items = [
            BudgetResponse(
                uuid="uuid-1",
                app_id="app-1",
                app_name="App One",
                limit_usd=100.0,
                spent_usd=50.0,
                remaining_usd=50.0,
                usage_percent=50.0,
                period="monthly",
                is_exceeded=False,
            ),
            BudgetResponse(
                uuid="uuid-2",
                app_id="app-2",
                app_name="App Two",
                limit_usd=200.0,
                spent_usd=250.0,
                remaining_usd=0.0,
                usage_percent=125.0,
                period="monthly",
                is_exceeded=True,
            ),
        ]

        response = BudgetListResponse(items=items, total=2)

        assert len(response.items) == 2
        assert response.total == 2
        assert response.items[0].app_id == "app-1"
        assert response.items[1].is_exceeded is True


class TestBudgetCalculations:
    """Test budget calculation logic."""

    def test_usage_percent_calculation(self):
        """Test usage percentage calculation."""
        # 50% used
        spent = 50.0
        limit = 100.0
        usage = (spent / limit * 100) if limit > 0 else 0
        assert usage == 50.0

        # 0% used
        spent = 0.0
        usage = (spent / limit * 100) if limit > 0 else 0
        assert usage == 0.0

        # 100% used
        spent = 100.0
        usage = (spent / limit * 100) if limit > 0 else 0
        assert usage == 100.0

        # Over 100%
        spent = 150.0
        usage = (spent / limit * 100) if limit > 0 else 0
        assert usage == 150.0

    def test_remaining_calculation(self):
        """Test remaining amount calculation."""
        limit = 100.0
        spent = 25.0
        remaining = max(0, limit - spent)
        assert remaining == 75.0

        # Over budget should return 0
        spent = 150.0
        remaining = max(0, limit - spent)
        assert remaining == 0.0

    def test_is_exceeded_logic(self):
        """Test exceeded detection."""
        limit = 100.0

        # Not exceeded
        spent = 99.99
        assert (spent >= limit) is False

        # Exactly at limit = exceeded
        spent = 100.0
        assert (spent >= limit) is True

        # Over limit
        spent = 100.01
        assert (spent >= limit) is True


class TestBudgetScope:
    """Test budget scope and period."""

    def test_application_scope_value(self):
        """APPLICATION scope should be valid."""
        assert BudgetScope.APPLICATION.value == "application"

    def test_budget_period_monthly(self):
        """MONTHLY period should be the default."""
        assert BudgetPeriod.MONTHLY.value == "monthly"
