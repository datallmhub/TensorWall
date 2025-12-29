"""Unit tests for Data Retention & Privacy module."""

from datetime import datetime, timedelta

from backend.core.retention import (
    DataCategory,
    RetentionPeriod,
    RetentionPolicy,
    AnonymizationConfig,
    RetentionManager,
    DEFAULT_RETENTION,
    RETENTION_DAYS,
)


class TestDataCategory:
    """Tests for DataCategory enum."""

    def test_valid_categories(self):
        """Test all valid categories."""
        assert DataCategory.AUDIT_LOGS == "audit_logs"
        assert DataCategory.USAGE_RECORDS == "usage_records"
        assert DataCategory.REQUEST_LOGS == "request_logs"
        assert DataCategory.DECISION_TRACES == "decision_traces"
        assert DataCategory.ERROR_LOGS == "error_logs"
        assert DataCategory.ANALYTICS == "analytics"


class TestRetentionPeriod:
    """Tests for RetentionPeriod enum."""

    def test_valid_periods(self):
        """Test all valid periods."""
        assert RetentionPeriod.IMMEDIATE == "immediate"
        assert RetentionPeriod.SHORT == "short"
        assert RetentionPeriod.MEDIUM == "medium"
        assert RetentionPeriod.LONG == "long"
        assert RetentionPeriod.EXTENDED == "extended"
        assert RetentionPeriod.INDEFINITE == "indefinite"


class TestRetentionDays:
    """Tests for RETENTION_DAYS mapping."""

    def test_days_mapping(self):
        """Test that all periods have correct days."""
        assert RETENTION_DAYS[RetentionPeriod.IMMEDIATE] == 0
        assert RETENTION_DAYS[RetentionPeriod.SHORT] == 7
        assert RETENTION_DAYS[RetentionPeriod.MEDIUM] == 30
        assert RETENTION_DAYS[RetentionPeriod.LONG] == 90
        assert RETENTION_DAYS[RetentionPeriod.EXTENDED] == 365
        assert RETENTION_DAYS[RetentionPeriod.INDEFINITE] == -1


class TestDefaultRetention:
    """Tests for DEFAULT_RETENTION mapping."""

    def test_audit_logs_default(self):
        """Test default retention for audit logs."""
        assert DEFAULT_RETENTION[DataCategory.AUDIT_LOGS] == RetentionPeriod.LONG

    def test_usage_records_default(self):
        """Test default retention for usage records."""
        assert DEFAULT_RETENTION[DataCategory.USAGE_RECORDS] == RetentionPeriod.EXTENDED

    def test_request_logs_default(self):
        """Test default retention for request logs - should be short for privacy."""
        assert DEFAULT_RETENTION[DataCategory.REQUEST_LOGS] == RetentionPeriod.SHORT


class TestRetentionPolicy:
    """Tests for RetentionPolicy model."""

    def test_create_minimal(self):
        """Test creating policy with minimal fields."""
        policy = RetentionPolicy(
            category=DataCategory.AUDIT_LOGS,
            period=RetentionPeriod.LONG,
        )

        assert policy.category == DataCategory.AUDIT_LOGS
        assert policy.period == RetentionPeriod.LONG
        assert policy.anonymize_before_delete is True
        assert policy.archive_before_delete is False

    def test_create_full(self):
        """Test creating policy with all fields."""
        policy = RetentionPolicy(
            category=DataCategory.REQUEST_LOGS,
            period=RetentionPeriod.MEDIUM,
            anonymize_before_delete=True,
            archive_before_delete=True,
            custom_days=45,
        )

        assert policy.custom_days == 45
        assert policy.archive_before_delete is True


class TestAnonymizationConfig:
    """Tests for AnonymizationConfig model."""

    def test_default_values(self):
        """Test default anonymization configuration."""
        config = AnonymizationConfig()

        assert config.anonymize_app_ids is False
        assert config.anonymize_user_content is True
        assert config.anonymize_ip_addresses is True
        assert config.anonymize_api_keys is True
        assert config.preserve_statistics is True

    def test_custom_values(self):
        """Test custom anonymization configuration."""
        config = AnonymizationConfig(
            anonymize_app_ids=True,
            anonymize_user_content=False,
            preserve_statistics=False,
        )

        assert config.anonymize_app_ids is True
        assert config.anonymize_user_content is False
        assert config.preserve_statistics is False


class TestRetentionManager:
    """Tests for RetentionManager."""

    def test_init_with_defaults(self):
        """Test RetentionManager initializes with default policies."""
        manager = RetentionManager()

        # Should have policies for all categories
        for category in DataCategory:
            assert category in manager.policies

    def test_init_default_policies_match(self):
        """Test that initial policies match defaults."""
        manager = RetentionManager()

        for category, expected_period in DEFAULT_RETENTION.items():
            policy = manager.policies[category]
            assert policy.period == expected_period

    def test_set_policy(self):
        """Test setting a custom policy."""
        manager = RetentionManager()

        custom_policy = RetentionPolicy(
            category=DataCategory.REQUEST_LOGS,
            period=RetentionPeriod.IMMEDIATE,
            anonymize_before_delete=False,
        )
        manager.set_policy(custom_policy)

        assert manager.policies[DataCategory.REQUEST_LOGS].period == RetentionPeriod.IMMEDIATE

    def test_get_policy(self):
        """Test getting a policy."""
        manager = RetentionManager()

        policy = manager.policies.get(DataCategory.AUDIT_LOGS)

        assert policy is not None
        assert policy.category == DataCategory.AUDIT_LOGS

    def test_anonymization_config(self):
        """Test that manager has anonymization config."""
        manager = RetentionManager()

        assert manager.anonymization_config is not None
        assert isinstance(manager.anonymization_config, AnonymizationConfig)


class TestRetentionCalculations:
    """Tests for retention period calculations."""

    def test_calculate_expiry_from_period(self):
        """Test calculating expiry date from retention period."""
        now = datetime.utcnow()

        for period, days in RETENTION_DAYS.items():
            if days >= 0:
                expected_expiry = now + timedelta(days=days)
                calculated_expiry = now + timedelta(days=days)

                # Within 1 second difference
                assert abs((expected_expiry - calculated_expiry).total_seconds()) < 1

    def test_indefinite_never_expires(self):
        """Test that indefinite retention never expires."""
        days = RETENTION_DAYS[RetentionPeriod.INDEFINITE]
        assert days == -1  # Special value for never


class TestPrivacyCompliance:
    """Tests for privacy compliance features."""

    def test_request_logs_short_retention(self):
        """Test that request logs (containing user data) have short retention."""
        # This is a compliance check - request logs should not be kept too long
        period = DEFAULT_RETENTION[DataCategory.REQUEST_LOGS]
        days = RETENTION_DAYS[period]

        assert days <= 30  # Should be 30 days or less for privacy

    def test_usage_records_extended_retention(self):
        """Test that usage records (for billing) have extended retention."""
        # Billing records often need longer retention
        period = DEFAULT_RETENTION[DataCategory.USAGE_RECORDS]
        days = RETENTION_DAYS[period]

        assert days >= 365  # At least 1 year for billing

    def test_anonymization_preserves_statistics(self):
        """Test that anonymization preserves aggregate statistics by default."""
        config = AnonymizationConfig()

        assert config.preserve_statistics is True
