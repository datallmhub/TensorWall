"""Data Retention & Privacy Policies.

Manages data lifecycle:
- Retention periods
- Automatic cleanup
- Data anonymization
- Export restrictions
"""

from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel
from enum import Enum
import hashlib
import re


class DataCategory(str, Enum):
    """Categories of data with different retention policies."""

    AUDIT_LOGS = "audit_logs"
    USAGE_RECORDS = "usage_records"
    REQUEST_LOGS = "request_logs"  # With prompts
    DECISION_TRACES = "decision_traces"
    ERROR_LOGS = "error_logs"
    ANALYTICS = "analytics"


class RetentionPeriod(str, Enum):
    """Standard retention periods."""

    IMMEDIATE = "immediate"  # Delete after processing
    SHORT = "short"  # 7 days
    MEDIUM = "medium"  # 30 days
    LONG = "long"  # 90 days
    EXTENDED = "extended"  # 1 year
    INDEFINITE = "indefinite"  # Never auto-delete


# Default retention periods by category
DEFAULT_RETENTION = {
    DataCategory.AUDIT_LOGS: RetentionPeriod.LONG,  # 90 days
    DataCategory.USAGE_RECORDS: RetentionPeriod.EXTENDED,  # 1 year (billing)
    DataCategory.REQUEST_LOGS: RetentionPeriod.SHORT,  # 7 days (privacy)
    DataCategory.DECISION_TRACES: RetentionPeriod.MEDIUM,  # 30 days
    DataCategory.ERROR_LOGS: RetentionPeriod.MEDIUM,  # 30 days
    DataCategory.ANALYTICS: RetentionPeriod.EXTENDED,  # 1 year
}

# Retention period to days mapping
RETENTION_DAYS = {
    RetentionPeriod.IMMEDIATE: 0,
    RetentionPeriod.SHORT: 7,
    RetentionPeriod.MEDIUM: 30,
    RetentionPeriod.LONG: 90,
    RetentionPeriod.EXTENDED: 365,
    RetentionPeriod.INDEFINITE: -1,  # Never
}


class RetentionPolicy(BaseModel):
    """Retention policy configuration."""

    category: DataCategory
    period: RetentionPeriod
    anonymize_before_delete: bool = True
    archive_before_delete: bool = False
    custom_days: Optional[int] = None  # Override standard period


class AnonymizationConfig(BaseModel):
    """Configuration for data anonymization."""

    anonymize_app_ids: bool = False
    anonymize_user_content: bool = True
    anonymize_ip_addresses: bool = True
    anonymize_api_keys: bool = True
    preserve_statistics: bool = True  # Keep aggregated data


class RetentionManager:
    """
    Manages data retention and privacy.

    Features:
    - Configurable retention periods per data category
    - Automatic data cleanup
    - Data anonymization
    - Compliance support (GDPR, etc.)
    """

    def __init__(self):
        self.policies: dict[DataCategory, RetentionPolicy] = {}
        self.anonymization_config = AnonymizationConfig()

        # Initialize with defaults
        for category, period in DEFAULT_RETENTION.items():
            self.policies[category] = RetentionPolicy(
                category=category,
                period=period,
            )

    def set_policy(self, policy: RetentionPolicy) -> None:
        """Set or update a retention policy."""
        self.policies[policy.category] = policy

    def get_policy(self, category: DataCategory) -> RetentionPolicy:
        """Get the retention policy for a category."""
        return self.policies.get(
            category,
            RetentionPolicy(
                category=category,
                period=RetentionPeriod.MEDIUM,
            ),
        )

    def get_retention_days(self, category: DataCategory) -> int:
        """Get the number of days to retain data for a category."""
        policy = self.get_policy(category)
        if policy.custom_days is not None:
            return policy.custom_days
        return RETENTION_DAYS.get(policy.period, 30)

    def get_cutoff_date(self, category: DataCategory) -> Optional[datetime]:
        """Get the cutoff date for data deletion."""
        days = self.get_retention_days(category)
        if days < 0:  # Indefinite
            return None
        return datetime.utcnow() - timedelta(days=days)

    def should_delete(self, category: DataCategory, timestamp: datetime) -> bool:
        """Check if data should be deleted based on timestamp."""
        cutoff = self.get_cutoff_date(category)
        if cutoff is None:
            return False
        return timestamp < cutoff

    def anonymize_data(self, data: dict) -> dict:
        """
        Anonymize sensitive data in a record.

        Returns a new dict with anonymized values.
        """
        result = data.copy()
        config = self.anonymization_config

        if config.anonymize_user_content:
            # Anonymize message content
            if "content" in result:
                result["content"] = self._anonymize_text(result["content"])
            if "messages" in result:
                result["messages"] = [
                    {**m, "content": self._anonymize_text(m.get("content", ""))}
                    for m in result["messages"]
                ]
            if "prompt" in result:
                result["prompt"] = self._anonymize_text(result["prompt"])

        if config.anonymize_ip_addresses:
            if "ip_address" in result:
                result["ip_address"] = self._anonymize_ip(result["ip_address"])
            if "client_ip" in result:
                result["client_ip"] = self._anonymize_ip(result["client_ip"])

        if config.anonymize_api_keys:
            if "api_key" in result:
                result["api_key"] = self._anonymize_key(result["api_key"])

        if config.anonymize_app_ids:
            if "app_id" in result:
                result["app_id"] = self._hash_value(result["app_id"])

        return result

    def _anonymize_text(self, text: str) -> str:
        """Anonymize text content while preserving structure."""
        if not text:
            return text

        # Anonymize emails
        text = re.sub(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL]", text
        )

        # Anonymize phone numbers
        text = re.sub(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "[PHONE]", text)

        # Anonymize credit card numbers
        text = re.sub(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", "[CARD]", text)

        # Anonymize SSN
        text = re.sub(r"\b\d{3}[-]?\d{2}[-]?\d{4}\b", "[SSN]", text)

        # Anonymize API keys and tokens
        text = re.sub(
            r"\b(sk-|pk-|api_|key_|token_)[A-Za-z0-9]{20,}\b", "[API_KEY]", text
        )

        return text

    def _anonymize_ip(self, ip: str) -> str:
        """Anonymize IP address (zero last octet for IPv4)."""
        if not ip:
            return ip
        parts = ip.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.{parts[2]}.0"
        return self._hash_value(ip)[:16]

    def _anonymize_key(self, key: str) -> str:
        """Anonymize API key (show prefix only)."""
        if not key:
            return key
        if len(key) > 8:
            return f"{key[:8]}..."
        return "***"

    def _hash_value(self, value: str) -> str:
        """Hash a value for anonymization."""
        return hashlib.sha256(value.encode()).hexdigest()[:16]


class DataExporter:
    """
    Exports data for compliance requests (GDPR, etc.).

    Features:
    - Export all data for a user/app
    - Anonymization during export
    - Format conversion (JSON, CSV)
    """

    def __init__(self, retention_manager: RetentionManager):
        self.retention = retention_manager

    def export_app_data(
        self,
        app_id: str,
        audit_logs: list[dict],
        usage_records: list[dict],
        anonymize: bool = False,
    ) -> dict:
        """
        Export all data for an application.

        Args:
            app_id: Application ID
            audit_logs: Audit log records
            usage_records: Usage records
            anonymize: Whether to anonymize data

        Returns:
            Exported data structure
        """
        export_data = {
            "export_timestamp": datetime.utcnow().isoformat(),
            "app_id": app_id,
            "data": {
                "audit_logs": [],
                "usage_records": [],
            },
            "retention_policies": {},
        }

        # Add retention policies info
        for category in DataCategory:
            policy = self.retention.get_policy(category)
            export_data["retention_policies"][category.value] = {
                "period": policy.period.value,
                "days": self.retention.get_retention_days(category),
            }

        # Export audit logs
        for log in audit_logs:
            if anonymize:
                log = self.retention.anonymize_data(log)
            export_data["data"]["audit_logs"].append(log)

        # Export usage records
        for record in usage_records:
            if anonymize:
                record = self.retention.anonymize_data(record)
            export_data["data"]["usage_records"].append(record)

        return export_data

    def export_to_csv(self, records: list[dict]) -> str:
        """Export records to CSV format."""
        if not records:
            return ""

        import csv
        import io

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)
        return output.getvalue()


class DataDeletionManager:
    """
    Manages data deletion for compliance.

    Supports:
    - Right to be forgotten (GDPR Article 17)
    - Selective deletion by category
    - Audit trail of deletions
    """

    def __init__(self, retention_manager: RetentionManager):
        self.retention = retention_manager
        self.deletion_log: list[dict] = []

    def request_deletion(
        self,
        app_id: str,
        categories: Optional[list[DataCategory]] = None,
        reason: str = "user_request",
    ) -> dict:
        """
        Request deletion of data for an application.

        Args:
            app_id: Application ID
            categories: Specific categories to delete (None = all)
            reason: Reason for deletion

        Returns:
            Deletion request record
        """
        request = {
            "request_id": hashlib.sha256(
                f"{app_id}:{datetime.utcnow().isoformat()}".encode()
            ).hexdigest()[:16],
            "app_id": app_id,
            "categories": [c.value for c in (categories or list(DataCategory))],
            "reason": reason,
            "requested_at": datetime.utcnow().isoformat(),
            "status": "pending",
        }

        self.deletion_log.append(request)
        return request

    def execute_deletion(
        self,
        request_id: str,
        deleted_counts: dict[str, int],
    ) -> dict:
        """
        Record execution of a deletion request.

        Args:
            request_id: Deletion request ID
            deleted_counts: Counts of deleted records by category

        Returns:
            Updated deletion record
        """
        for request in self.deletion_log:
            if request["request_id"] == request_id:
                request["status"] = "completed"
                request["completed_at"] = datetime.utcnow().isoformat()
                request["deleted_counts"] = deleted_counts
                return request

        return {"error": "Request not found"}

    def get_deletion_log(self, app_id: Optional[str] = None) -> list[dict]:
        """Get deletion log, optionally filtered by app."""
        if app_id:
            return [r for r in self.deletion_log if r["app_id"] == app_id]
        return self.deletion_log


# Singleton instances
retention_manager = RetentionManager()
data_exporter = DataExporter(retention_manager)
deletion_manager = DataDeletionManager(retention_manager)
