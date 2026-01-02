"""Initial schema

Revision ID: 001_initial
Revises:
Create Date: 2024-12-29

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    environment_enum = postgresql.ENUM(
        "development", "staging", "production", name="environment", create_type=False
    )
    environment_enum.create(op.get_bind(), checkfirst=True)

    budget_period_enum = postgresql.ENUM(
        "hourly", "daily", "weekly", "monthly", name="budgetperiod", create_type=False
    )
    budget_period_enum.create(op.get_bind(), checkfirst=True)

    budget_scope_enum = postgresql.ENUM(
        "APPLICATION",
        "USER",
        "FEATURE",
        "ORGANIZATION",
        name="budgetscope",
        create_type=False,
    )
    budget_scope_enum.create(op.get_bind(), checkfirst=True)

    policy_action_enum = postgresql.ENUM(
        "allow", "warn", "deny", name="policyaction", create_type=False
    )
    policy_action_enum.create(op.get_bind(), checkfirst=True)

    rule_type_enum = postgresql.ENUM(
        "model_restriction",
        "environment_restriction",
        "feature_restriction",
        "token_limit",
        "time_restriction",
        "general",
        name="ruletype",
        create_type=False,
    )
    rule_type_enum.create(op.get_bind(), checkfirst=True)

    audit_event_enum = postgresql.ENUM(
        "request",
        "response",
        "policy_decision",
        "budget_check",
        "security_check",
        "error",
        name="auditeventtype",
        create_type=False,
    )
    audit_event_enum.create(op.get_bind(), checkfirst=True)

    trace_decision_enum = postgresql.ENUM(
        "allow", "warn", "block", "degrade", name="tracedecision", create_type=False
    )
    trace_decision_enum.create(op.get_bind(), checkfirst=True)

    trace_status_enum = postgresql.ENUM(
        "pending",
        "success",
        "blocked",
        "error",
        "timeout",
        name="tracestatus",
        create_type=False,
    )
    trace_status_enum.create(op.get_bind(), checkfirst=True)

    tenant_status_enum = postgresql.ENUM(
        "ACTIVE", "SUSPENDED", "DELETED", name="tenantstatus", create_type=False
    )
    tenant_status_enum.create(op.get_bind(), checkfirst=True)

    tenant_tier_enum = postgresql.ENUM(
        "FREE",
        "STARTER",
        "PROFESSIONAL",
        "ENTERPRISE",
        name="tenanttier",
        create_type=False,
    )
    tenant_tier_enum.create(op.get_bind(), checkfirst=True)

    # Users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="user"),
        sa.Column("permissions", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # Organizations table
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("org_id", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "SUSPENDED", "DELETED", name="tenantstatus"),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column(
            "tier",
            sa.Enum("FREE", "STARTER", "PROFESSIONAL", "ENTERPRISE", name="tenanttier"),
            nullable=False,
            server_default="FREE",
        ),
        sa.Column("owner_email", sa.String(length=255), nullable=True),
        sa.Column("billing_email", sa.String(length=255), nullable=True),
        sa.Column("technical_contact", sa.String(length=255), nullable=True),
        sa.Column("max_applications", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("max_users", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("max_api_keys", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("max_environments", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("custom_domain", sa.String(length=255), nullable=True),
        sa.Column("sso_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "audit_retention_days", sa.Integer(), nullable=False, server_default="30"
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id"),
        sa.UniqueConstraint("slug"),
    )

    # Applications table
    op.create_table(
        "applications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("app_id", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("owner", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("allowed_providers", sa.JSON(), nullable=True),
        sa.Column("allowed_models", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("app_id"),
        sa.UniqueConstraint("uuid"),
    )

    # API Keys table
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key_hash", sa.String(length=255), nullable=False),
        sa.Column("key_prefix", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column(
            "environment",
            sa.Enum("development", "staging", "production", name="environment"),
            nullable=False,
            server_default="development",
        ),
        sa.Column("llm_api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"], ["applications.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash"),
    )
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"], unique=True)
    op.create_index("ix_api_keys_key_prefix", "api_keys", ["key_prefix"], unique=False)

    # Policy Rules table
    op.create_table(
        "policy_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "rule_type",
            sa.Enum(
                "model_restriction",
                "environment_restriction",
                "feature_restriction",
                "token_limit",
                "time_restriction",
                "general",
                name="ruletype",
            ),
            nullable=False,
        ),
        sa.Column(
            "action",
            sa.Enum("allow", "warn", "deny", name="policyaction"),
            nullable=False,
        ),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("conditions", sa.JSON(), nullable=True),
        sa.Column("app_id", sa.String(length=100), nullable=True),
        sa.Column("user_email", sa.String(length=255), nullable=True),
        sa.Column("model_pattern", sa.String(length=255), nullable=True),
        sa.Column("environment", sa.String(length=50), nullable=True),
        sa.Column("feature", sa.String(length=100), nullable=True),
        sa.Column("max_tokens", sa.Integer(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index("ix_policy_rules_app_id", "policy_rules", ["app_id"], unique=False)
    op.create_index(
        "ix_policy_rules_user_email", "policy_rules", ["user_email"], unique=False
    )

    # Budgets table
    op.create_table(
        "budgets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "scope",
            sa.Enum(
                "APPLICATION", "USER", "FEATURE", "ORGANIZATION", name="budgetscope"
            ),
            nullable=False,
        ),
        sa.Column("application_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("user_email", sa.String(length=255), nullable=True),
        sa.Column("org_id", sa.String(length=100), nullable=True),
        sa.Column("feature", sa.String(length=100), nullable=True),
        sa.Column(
            "environment",
            sa.Enum("development", "staging", "production", name="environment"),
            nullable=True,
        ),
        sa.Column("soft_limit_usd", sa.Float(), nullable=False),
        sa.Column("hard_limit_usd", sa.Float(), nullable=False),
        sa.Column(
            "period",
            sa.Enum("hourly", "daily", "weekly", "monthly", name="budgetperiod"),
            nullable=False,
            server_default="monthly",
        ),
        sa.Column(
            "current_spend_usd", sa.Float(), nullable=False, server_default="0.0"
        ),
        sa.Column("period_start", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"], ["applications.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )

    # Audit Logs table
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "event_type",
            sa.Enum(
                "request",
                "response",
                "policy_decision",
                "budget_check",
                "security_check",
                "error",
                name="auditeventtype",
            ),
            nullable=False,
        ),
        sa.Column("app_id", sa.String(length=100), nullable=True),
        sa.Column("user_email", sa.String(length=255), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=True),
        sa.Column("request_id", sa.String(length=100), nullable=True),
        sa.Column("event_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index("ix_audit_logs_app_id", "audit_logs", ["app_id"], unique=False)
    op.create_index(
        "ix_audit_logs_created_at", "audit_logs", ["created_at"], unique=False
    )
    op.create_index(
        "ix_audit_logs_request_id", "audit_logs", ["request_id"], unique=False
    )

    # Usage Records table
    op.create_table(
        "usage_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=True),
        sa.Column("app_id", sa.String(length=100), nullable=True),
        sa.Column("user_email", sa.String(length=255), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=True),
        sa.Column("feature", sa.String(length=100), nullable=True),
        sa.Column("environment", sa.String(length=50), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("request_id", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"], ["applications.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index(
        "ix_usage_records_app_id", "usage_records", ["app_id"], unique=False
    )
    op.create_index(
        "ix_usage_records_created_at", "usage_records", ["created_at"], unique=False
    )

    # Request Traces table
    op.create_table(
        "request_traces",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.String(length=100), nullable=False),
        sa.Column("app_id", sa.String(length=100), nullable=True),
        sa.Column("org_id", sa.String(length=100), nullable=True),
        sa.Column("user_email", sa.String(length=255), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=True),
        sa.Column("feature", sa.String(length=100), nullable=True),
        sa.Column("environment", sa.String(length=50), nullable=True),
        sa.Column(
            "decision",
            sa.Enum("allow", "warn", "block", "degrade", name="tracedecision"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "success", "blocked", "error", "timeout", name="tracestatus"
            ),
            nullable=False,
        ),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("gateway_latency_ms", sa.Float(), nullable=True),
        sa.Column("policy_violations", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("prompt_preview", sa.Text(), nullable=True),
        sa.Column("response_preview", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id"),
    )
    op.create_index(
        "ix_request_traces_app_id", "request_traces", ["app_id"], unique=False
    )
    op.create_index(
        "ix_request_traces_created_at", "request_traces", ["created_at"], unique=False
    )
    op.create_index(
        "ix_request_traces_decision", "request_traces", ["decision"], unique=False
    )
    op.create_index(
        "ix_request_traces_model", "request_traces", ["model"], unique=False
    )
    op.create_index(
        "ix_request_traces_status", "request_traces", ["status"], unique=False
    )

    # Model Registry table
    op.create_table(
        "model_registry",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("model_id", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("context_window", sa.Integer(), nullable=True),
        sa.Column("max_output_tokens", sa.Integer(), nullable=True),
        sa.Column("input_cost_per_1k", sa.Float(), nullable=True),
        sa.Column("output_cost_per_1k", sa.Float(), nullable=True),
        sa.Column(
            "supports_streaming", sa.Boolean(), nullable=False, server_default="true"
        ),
        sa.Column(
            "supports_functions", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "supports_vision", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_id"),
    )

    # Features table
    op.create_table(
        "features",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"], ["applications.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_features_app_feature", "features", ["application_id", "name"], unique=True
    )

    # Setup State table
    op.create_table(
        "setup_state",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )


def downgrade() -> None:
    op.drop_table("setup_state")
    op.drop_table("features")
    op.drop_table("model_registry")
    op.drop_table("request_traces")
    op.drop_table("usage_records")
    op.drop_table("audit_logs")
    op.drop_table("budgets")
    op.drop_table("policy_rules")
    op.drop_table("api_keys")
    op.drop_table("applications")
    op.drop_table("organizations")
    op.drop_table("users")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS tenanttier")
    op.execute("DROP TYPE IF EXISTS tenantstatus")
    op.execute("DROP TYPE IF EXISTS tracestatus")
    op.execute("DROP TYPE IF EXISTS tracedecision")
    op.execute("DROP TYPE IF EXISTS auditeventtype")
    op.execute("DROP TYPE IF EXISTS ruletype")
    op.execute("DROP TYPE IF EXISTS policyaction")
    op.execute("DROP TYPE IF EXISTS budgetscope")
    op.execute("DROP TYPE IF EXISTS budgetperiod")
    op.execute("DROP TYPE IF EXISTS environment")
