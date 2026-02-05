import smtplib
from email.message import EmailMessage

from backend.core.config import settings
from backend.domain.models import Budget


class BudgetNotificationService:
    """Handles budget threshold email notifications."""

    WARNING_THRESHOLD = 80
    CRITICAL_THRESHOLD = 100

    def notify_if_needed(self, budget: Budget) -> None:
        """Send alert email if budget crosses thresholds."""
        percent = budget.usage_percent

        if percent < self.WARNING_THRESHOLD:
            return

        subject, body = self._build_message(percent)

        msg = EmailMessage()
        msg["From"] = settings.ALERT_FROM_EMAIL
        msg["To"] = "admin@tensorwall.local"  # placeholder; can be app/org email later
        msg["Subject"] = subject
        msg.set_content(body)

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USER:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)

    def _build_message(self, percent: float) -> tuple[str, str]:
        if percent >= self.CRITICAL_THRESHOLD:
            return (
                "Budget Limit Reached",
                f"Your budget has reached {percent:.0f}% usage. Spending may be blocked.",
            )
        return (
            "Budget Usage Warning",
            f"Your budget has reached {percent:.0f}% usage.",
        )
