from unittest.mock import patch, MagicMock

from backend.application.services.budget_notification_service import (
    BudgetNotificationService,
)


def test_email_triggered_at_80_percent():
    service = BudgetNotificationService()

    mock_budget = MagicMock()
    mock_budget.usage_percent = 85

    with patch("smtplib.SMTP") as mock_smtp:
        service.notify_if_needed(mock_budget)
        assert mock_smtp.called


def test_no_email_below_threshold():
    service = BudgetNotificationService()

    mock_budget = MagicMock()
    mock_budget.usage_percent = 50

    with patch("smtplib.SMTP") as mock_smtp:
        service.notify_if_needed(mock_budget)
        assert not mock_smtp.called
