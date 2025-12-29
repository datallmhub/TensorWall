"""LLM Gateway SDK exceptions."""

from typing import Optional, Dict, Any


class LLMGatewayError(Exception):
    """Base exception for LLM Gateway SDK."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body or {}

    def __str__(self) -> str:
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
        return self.message


class AuthenticationError(LLMGatewayError):
    """Raised when authentication fails (401/403)."""
    pass


class RateLimitError(LLMGatewayError):
    """Raised when rate limit is exceeded (429)."""

    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class ValidationError(LLMGatewayError):
    """Raised when request validation fails (400/422)."""
    pass


class ServerError(LLMGatewayError):
    """Raised when server returns an error (5xx)."""
    pass


class PolicyDeniedError(LLMGatewayError):
    """Raised when request is denied by policy engine."""

    def __init__(
        self,
        message: str,
        policy_name: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.policy_name = policy_name


class BudgetExceededError(LLMGatewayError):
    """Raised when budget limit is exceeded."""

    def __init__(
        self,
        message: str,
        budget_type: Optional[str] = None,
        limit: Optional[float] = None,
        current: Optional[float] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.budget_type = budget_type
        self.limit = limit
        self.current = current
