from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List
from functools import lru_cache
import warnings


class Settings(BaseSettings):
    # Environment
    environment: str = "development"
    debug: bool = True

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/tensorwall"
    redis_url: str = "redis://localhost:6379"

    # LLM Providers (for passthrough)
    openai_api_url: str = "https://api.openai.com/v1"
    anthropic_api_url: str = "https://api.anthropic.com/v1"
    ollama_api_url: str = "http://host.docker.internal:11434"

    # Gateway settings
    max_latency_ms: int = 50
    default_max_tokens: int = 4096
    default_max_context: int = 128000

    # Audit
    audit_retention_days: int = 90
    store_prompts: bool = False  # GDPR/security: off by default

    # Email Alerts (SMTP)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    ALERT_FROM_EMAIL: str = "alerts@tensorwall.io"

    # JWT Authentication
    jwt_secret_key: str = "dev-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Cookie settings
    cookie_secure: bool = False  # Set True in production (HTTPS)
    cookie_httponly: bool = True
    cookie_samesite: str = "lax"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        """Warn if using default secret in production."""
        # Access environment from values if available
        return v

    def validate_production_settings(self) -> list[str]:
        """Validate settings for production deployment. Returns list of warnings."""
        issues = []

        if self.environment == "production":
            if self.debug:
                issues.append("SECURITY: debug=True in production environment")

            if self.jwt_secret_key == "dev-secret-key-change-in-production":
                issues.append("CRITICAL: Using default jwt_secret_key in production!")

            if not self.cookie_secure:
                issues.append(
                    "SECURITY: cookie_secure=False in production (should be True for HTTPS)"
                )

            if "localhost" in str(self.cors_origins):
                issues.append("WARNING: localhost in CORS origins in production")

        return issues


@lru_cache()
def get_settings() -> Settings:
    instance = Settings()

    # Validate production settings
    issues = instance.validate_production_settings()
    for issue in issues:
        warnings.warn(issue, RuntimeWarning)

    return instance


settings = get_settings()
