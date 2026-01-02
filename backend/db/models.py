"""SQLAlchemy models for TensorWall."""

from datetime import datetime
from typing import Optional
import uuid as uuid_lib
from sqlalchemy import (
    String,
    Text,
    Boolean,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    JSON,
    Index,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


# Constants
CASCADE_DELETE_ORPHAN = "all, delete-orphan"


class Environment(str, enum.Enum):
    """Environment types."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class BudgetPeriod(str, enum.Enum):
    """Budget period types."""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class PolicyAction(str, enum.Enum):
    """Policy decision actions."""

    ALLOW = "allow"
    WARN = "warn"
    DENY = "deny"


class RuleType(str, enum.Enum):
    """Rule type for policies."""

    MODEL_RESTRICTION = "model_restriction"
    ENVIRONMENT_RESTRICTION = "environment_restriction"
    FEATURE_RESTRICTION = "feature_restriction"
    TOKEN_LIMIT = "token_limit"
    TIME_RESTRICTION = "time_restriction"
    GENERAL = "general"


class AuditEventType(str, enum.Enum):
    """Audit event types."""

    REQUEST = "request"
    RESPONSE = "response"
    POLICY_DECISION = "policy_decision"
    BUDGET_CHECK = "budget_check"
    SECURITY_CHECK = "security_check"
    ERROR = "error"


class TraceDecision(str, enum.Enum):
    """LLM Request trace decision."""

    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"
    DEGRADE = "degrade"


class TraceStatus(str, enum.Enum):
    """LLM Request trace status."""

    PENDING = "pending"
    SUCCESS = "success"
    BLOCKED = "blocked"
    ERROR = "error"
    TIMEOUT = "timeout"


# ============================================================================
# Application & API Keys
# ============================================================================


class Application(Base):
    """Application registered in the gateway."""

    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, index=True, default=uuid_lib.uuid4
    )
    app_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    owner: Mapped[str] = mapped_column(String(255))  # team/service owner
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Settings
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    allowed_providers: Mapped[list] = mapped_column(
        JSON, default=["openai", "anthropic"]
    )
    allowed_models: Mapped[list] = mapped_column(JSON, default=[])  # Empty = all

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    api_keys: Mapped[list["ApiKey"]] = relationship(
        back_populates="application", cascade=CASCADE_DELETE_ORPHAN
    )
    budgets: Mapped[list["Budget"]] = relationship(
        back_populates="application", cascade=CASCADE_DELETE_ORPHAN
    )
    policy_rules: Mapped[list["PolicyRule"]] = relationship(
        back_populates="application", cascade=CASCADE_DELETE_ORPHAN
    )


class ApiKey(Base):
    """API keys for applications."""

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    key_hash: Mapped[str] = mapped_column(
        String(64), unique=True, index=True
    )  # SHA256 hash
    key_prefix: Mapped[str] = mapped_column(
        String(12)
    )  # First 8 chars for identification
    name: Mapped[str] = mapped_column(String(255))  # Human-readable name

    # Association
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"))
    application: Mapped["Application"] = relationship(back_populates="api_keys")

    # Scoping
    environment: Mapped[Environment] = mapped_column(
        SQLEnum(Environment), default=Environment.DEVELOPMENT
    )

    # LLM Provider credentials (optional - BYO key)
    llm_api_key_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("ix_api_keys_app_env", "application_id", "environment"),)


# ============================================================================
# Policy Rules
# ============================================================================


class PolicyRule(Base):
    """Policy rules for governance."""

    __tablename__ = "policy_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, index=True, default=uuid_lib.uuid4
    )
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Scope: global (null app_id) or per-application
    application_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("applications.id"), nullable=True
    )
    application: Mapped[Optional["Application"]] = relationship(
        back_populates="policy_rules"
    )

    # User-specific policy (optional)
    user_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Rule type (stored as string to match existing varchar column)
    rule_type: Mapped[str] = mapped_column(String(50), default="general")

    # Conditions (JSON for flexibility)
    conditions: Mapped[dict] = mapped_column(JSON, default={})
    # Example conditions:
    # {
    #   "environments": ["production"],
    #   "features": ["chat"],
    #   "models": ["gpt-4o"],
    #   "max_tokens": 4000,
    #   "max_context_tokens": 8000,
    #   "allowed_hours": [9, 18]
    # }

    # Decision
    action: Mapped[PolicyAction] = mapped_column(
        SQLEnum(PolicyAction), default=PolicyAction.ALLOW
    )
    priority: Mapped[int] = mapped_column(
        Integer, default=0
    )  # Higher = evaluated first

    # Status
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("ix_policy_rules_app_priority", "application_id", "priority"),
        Index(
            "ix_policy_rules_unique_app_user_type",
            "application_id",
            "user_email",
            "rule_type",
            unique=True,
        ),
    )


# ============================================================================
# Budgets
# ============================================================================


class BudgetScope(str, enum.Enum):
    """Budget scope types."""

    APPLICATION = "application"  # Budget for entire app
    USER = "user"  # Budget per user
    ORGANIZATION = "organization"  # Budget for org/team


class Budget(Base):
    """Budget limits - can be scoped to app, user, or organization."""

    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, index=True, default=uuid_lib.uuid4
    )

    # Scope type
    scope: Mapped[BudgetScope] = mapped_column(
        SQLEnum(BudgetScope), default=BudgetScope.APPLICATION
    )

    # Application scope (required for app budgets, optional for user/org)
    application_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("applications.id"), nullable=True
    )
    application: Mapped[Optional["Application"]] = relationship(
        back_populates="budgets"
    )

    # User scope (for per-user budgets)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    user_email: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )

    # Organization scope (for org/team budgets)
    org_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )

    # Additional filters
    feature: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )  # Null = all features
    environment: Mapped[Optional[Environment]] = mapped_column(
        SQLEnum(Environment), nullable=True
    )  # Null = all environments

    # Limits
    soft_limit_usd: Mapped[float] = mapped_column(Float)
    hard_limit_usd: Mapped[float] = mapped_column(Float)
    period: Mapped[BudgetPeriod] = mapped_column(
        SQLEnum(BudgetPeriod), default=BudgetPeriod.MONTHLY
    )

    # Current tracking
    current_spend_usd: Mapped[float] = mapped_column(Float, default=0.0)
    period_start: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("ix_budgets_app_feature_env", "application_id", "feature", "environment"),
        Index("ix_budgets_user", "user_id", "user_email"),
        Index("ix_budgets_org", "org_id"),
        Index("ix_budgets_scope", "scope"),
    )


# ============================================================================
# Usage & Audit
# ============================================================================


class UsageRecord(Base):
    """Individual usage records for tracking."""

    __tablename__ = "usage_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[str] = mapped_column(String(36), index=True)

    # Context
    app_id: Mapped[str] = mapped_column(String(100), index=True)
    feature: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    environment: Mapped[Environment] = mapped_column(SQLEnum(Environment))

    # LLM details
    provider: Mapped[str] = mapped_column(String(50))
    model: Mapped[str] = mapped_column(String(100))
    input_tokens: Mapped[int] = mapped_column(Integer)
    output_tokens: Mapped[int] = mapped_column(Integer)

    # Cost
    cost_usd: Mapped[float] = mapped_column(Float)

    # Performance
    latency_ms: Mapped[int] = mapped_column(Integer)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )

    __table_args__ = (
        Index("ix_usage_app_date", "app_id", "created_at"),
        Index("ix_usage_env_date", "environment", "created_at"),
    )


class AuditLog(Base):
    """Audit log for compliance and debugging."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[AuditEventType] = mapped_column(SQLEnum(AuditEventType))
    request_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, index=True
    )

    # Context
    app_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )
    feature: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    environment: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    owner: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Request details
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Decisions
    policy_decision: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    policy_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    budget_allowed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # Security
    security_issues: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)

    # Error
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Extra data (flexible storage)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )

    __table_args__ = (
        Index("ix_audit_app_type_date", "app_id", "event_type", "timestamp"),
    )


class LLMRequestTrace(Base):
    """
    Immutable trace of every LLM request - the single source of truth.

    This is the canonical request trace model that enables:
    - Full drill-down from dashboard to individual requests
    - Decision explainability and governance
    - Audit compliance (AI Act, SOC2, etc.)
    - Cost attribution and optimization

    Every request creates exactly ONE trace, whether blocked or successful.
    """

    __tablename__ = "llm_request_traces"

    # Identity
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    trace_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, index=True
    )  # OpenTelemetry compat

    # Context - Multi-tenant & Application
    tenant_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )
    app_id: Mapped[str] = mapped_column(String(100), index=True)
    feature: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    environment: Mapped[Environment] = mapped_column(SQLEnum(Environment), index=True)

    # Context - User & Session
    user_email: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    session_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # LLM Call Details
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)

    # Governance Decision
    decision: Mapped[TraceDecision] = mapped_column(SQLEnum(TraceDecision), index=True)
    decision_reasons: Mapped[list] = mapped_column(
        JSON, default=list
    )  # ["budget_exceeded", "prompt_injection"]
    risk_categories: Mapped[list] = mapped_column(
        JSON, default=list
    )  # ["pii_leakage", "data_exfiltration"]
    policies_evaluated: Mapped[list] = mapped_column(
        JSON, default=list
    )  # [{"id": 1, "name": "...", "result": "deny"}]

    # Budget & Cost
    budget_snapshot: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )  # Budget state at request time
    estimated_cost_avoided: Mapped[float] = mapped_column(
        Float, default=0.0
    )  # If blocked

    # Performance & Status
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[TraceStatus] = mapped_column(SQLEnum(TraceStatus), index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timing
    timestamp_start: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
    timestamp_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Extra metadata (renamed from 'metadata' to avoid SQLAlchemy reserved word)
    extra_metadata: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )  # Flexible storage

    __table_args__ = (
        # Core queries for dashboard
        Index("ix_trace_app_decision_date", "app_id", "decision", "timestamp_start"),
        Index("ix_trace_user_date", "user_email", "timestamp_start"),
        Index("ix_trace_status_date", "status", "timestamp_start"),
        # Governance queries
        Index(
            "ix_trace_tenant_env_date", "tenant_id", "environment", "timestamp_start"
        ),
        Index("ix_trace_feature_decision", "feature", "decision"),
        Index("ix_trace_model_date", "model", "timestamp_start"),
    )


# ============================================================================
# Notifications
# ============================================================================


class NotificationType(str, enum.Enum):
    """Notification types."""

    BUDGET_WARNING = "budget_warning"
    BUDGET_CRITICAL = "budget_critical"
    REQUEST_BLOCKED = "request_blocked"
    POLICY_VIOLATION = "policy_violation"
    SYSTEM = "system"
    INFO = "info"


class NotificationSeverity(str, enum.Enum):
    """Notification severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Notification(Base):
    """In-app notifications."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Type and severity
    type: Mapped[NotificationType] = mapped_column(SQLEnum(NotificationType))
    severity: Mapped[NotificationSeverity] = mapped_column(
        SQLEnum(NotificationSeverity), default=NotificationSeverity.INFO
    )

    # Content
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)

    # Context (optional)
    app_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )
    budget_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # Extra data
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Status
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    dismissed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (Index("ix_notifications_read_created", "read", "created_at"),)


# ============================================================================
# Multi-Tenancy / Organizations
# ============================================================================


class TenantStatus(str, enum.Enum):
    """Tenant status types."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    TRIAL = "trial"
    PENDING = "pending"
    CANCELLED = "cancelled"


class TenantTier(str, enum.Enum):
    """Tenant tier levels."""

    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    CUSTOM = "custom"


class Organization(Base):
    """Multi-tenant organization."""

    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)

    # Status
    status: Mapped[TenantStatus] = mapped_column(
        SQLEnum(TenantStatus), default=TenantStatus.ACTIVE
    )
    tier: Mapped[TenantTier] = mapped_column(
        SQLEnum(TenantTier), default=TenantTier.FREE
    )

    # Contacts
    owner_email: Mapped[str] = mapped_column(String(255))
    billing_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    technical_contact: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Limits
    max_applications: Mapped[int] = mapped_column(Integer, default=5)
    max_users: Mapped[int] = mapped_column(Integer, default=10)
    max_api_keys: Mapped[int] = mapped_column(Integer, default=20)
    max_environments: Mapped[int] = mapped_column(Integer, default=2)

    # Features
    allowed_features: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    blocked_features: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Settings
    custom_domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sso_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    audit_retention_days: Mapped[int] = mapped_column(Integer, default=30)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    members: Mapped[list["OrganizationMember"]] = relationship(
        back_populates="organization", cascade=CASCADE_DELETE_ORPHAN
    )
    tenant_applications: Mapped[list["TenantApplication"]] = relationship(
        back_populates="organization", cascade=CASCADE_DELETE_ORPHAN
    )


class OrganizationMember(Base):
    """Organization member."""

    __tablename__ = "organization_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    member_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)

    # Association
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    organization: Mapped["Organization"] = relationship(back_populates="members")

    # User info
    user_id: Mapped[str] = mapped_column(String(100), index=True)
    email: Mapped[str] = mapped_column(String(255))

    # Role
    role: Mapped[str] = mapped_column(String(50), default="member")
    permissions: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(20), default="active")
    invited_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    joined_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("ix_org_members_org_user", "organization_id", "user_id"),)


class TenantApplication(Base):
    """Application belonging to a tenant."""

    __tablename__ = "tenant_applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    app_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)

    # Association
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    organization: Mapped["Organization"] = relationship(
        back_populates="tenant_applications"
    )

    # Info
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Environments
    environments: Mapped[list] = mapped_column(
        JSON, default=["development", "production"]
    )

    # Limits
    budget_limit_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rate_limit_rpm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (Index("ix_tenant_apps_org", "organization_id"),)


# ============================================================================
# LLM Models Registry
# ============================================================================


class ProviderType(str, enum.Enum):
    """LLM Provider types."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MISTRAL = "mistral"
    OLLAMA = "ollama"
    LMSTUDIO = "lmstudio"
    AZURE_OPENAI = "azure_openai"
    AWS_BEDROCK = "aws_bedrock"
    GROQ = "groq"
    TOGETHER = "together"
    GOOGLE = "google"
    COHERE = "cohere"
    DEEPSEEK = "deepseek"
    XAI = "xai"
    CUSTOM = "custom"


class LLMModel(Base):
    """
    LLM Model registry - single source of truth for available models.

    This table defines which models are available in the gateway.
    Models can be:
    - Cloud providers (OpenAI, Anthropic)
    - Local providers (Ollama, LM Studio)
    - Custom endpoints (Azure OpenAI, self-hosted)
    """

    __tablename__ = "llm_models"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)

    # Display info
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Provider
    provider: Mapped[ProviderType] = mapped_column(SQLEnum(ProviderType))
    provider_model_id: Mapped[str] = mapped_column(
        String(255)
    )  # ID used by the provider API

    # Custom endpoint (for Azure, self-hosted, etc.)
    base_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    api_key_env_var: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # e.g., "AZURE_OPENAI_KEY"
    api_key: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # Direct API key storage

    # Capabilities
    context_length: Mapped[int] = mapped_column(Integer, default=4096)
    supports_vision: Mapped[bool] = mapped_column(Boolean, default=False)
    supports_functions: Mapped[bool] = mapped_column(Boolean, default=False)
    supports_streaming: Mapped[bool] = mapped_column(Boolean, default=True)

    # Pricing (per 1M tokens in USD)
    input_cost_per_million: Mapped[float] = mapped_column(Float, default=0.0)
    output_cost_per_million: Mapped[float] = mapped_column(Float, default=0.0)

    # Status
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(
        Boolean, default=False
    )  # Default model for new apps

    # Display order
    display_order: Mapped[int] = mapped_column(Integer, default=100)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("ix_llm_models_provider", "provider"),
        Index("ix_llm_models_enabled", "is_enabled"),
    )


# ============================================================================
# Feature Registry
# ============================================================================


class Feature(Base):
    """Feature/use-case definition."""

    __tablename__ = "features"

    id: Mapped[int] = mapped_column(primary_key=True)
    feature_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)

    # Scope
    app_id: Mapped[str] = mapped_column(String(100), index=True)

    # Definition
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Allowlisting
    allowed_actions: Mapped[list] = mapped_column(JSON, default=["generate"])
    allowed_models: Mapped[list] = mapped_column(JSON, default=[])
    allowed_environments: Mapped[list] = mapped_column(
        JSON, default=["development", "staging", "production"]
    )

    # Limits
    max_tokens_per_request: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    max_cost_per_request: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    daily_request_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    monthly_budget_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Status
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    require_contract: Mapped[bool] = mapped_column(Boolean, default=False)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (Index("ix_features_app", "app_id"),)


# ============================================================================
# User & RBAC
# ============================================================================


class UserRole(str, enum.Enum):
    """User roles for RBAC."""

    OWNER = "owner"
    ADMIN = "admin"
    SECURITY = "security"
    FINANCE = "finance"
    AUDITOR = "auditor"
    DEVELOPER = "developer"
    VIEWER = "viewer"
    SERVICE = "service"


class User(Base):
    """User account for admin access."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, index=True, default=uuid_lib.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # SSO / External auth
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    auth_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Global role
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.VIEWER)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    app_roles: Mapped[list["UserAppRole"]] = relationship(
        back_populates="user", cascade=CASCADE_DELETE_ORPHAN
    )

    __table_args__ = (Index("ix_users_external", "external_id", "auth_provider"),)


class UserAppRole(Base):
    """Per-application role assignment for users."""

    __tablename__ = "user_app_roles"

    id: Mapped[int] = mapped_column(primary_key=True)

    # User
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped["User"] = relationship(back_populates="app_roles")

    # Application
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"))

    # Role for this app (overrides global role)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole))

    # Additional permissions (JSON array of permission strings)
    additional_permissions: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    denied_permissions: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_user_app_roles_user_app", "user_id", "application_id", unique=True),
    )


# ============================================================================
# Setup State
# ============================================================================


class SetupState(Base):
    """
    Tracks gateway setup state.

    Used to determine if the gateway has been properly initialized
    via the CLI setup wizard.
    """

    __tablename__ = "setup_state"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    value: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
