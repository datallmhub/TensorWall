"""Tests for LLM Gateway SDK client."""

import pytest
from unittest.mock import patch, MagicMock
import httpx

from llm_gateway_sdk import LLMGateway, AsyncLLMGateway
from llm_gateway_sdk.models import ChatMessage, ChatCompletionResponse
from llm_gateway_sdk.exceptions import (
    AuthenticationError,
    RateLimitError,
    ValidationError,
    ServerError,
)


class TestLLMGatewayClient:
    """Tests for synchronous LLM Gateway client."""

    def test_init_default_values(self):
        """Test client initialization with defaults."""
        client = LLMGateway()
        assert client.base_url == "http://localhost:8000"
        assert client.api_key is None
        assert client.app_id is None
        assert client.timeout == 60.0
        client.close()

    def test_init_custom_values(self):
        """Test client initialization with custom values."""
        client = LLMGateway(
            base_url="https://api.example.com",
            api_key="test-key",
            app_id="my-app",
            org_id="my-org",
            timeout=30.0,
        )
        assert client.base_url == "https://api.example.com"
        assert client.api_key == "test-key"
        assert client.app_id == "my-app"
        assert client.org_id == "my-org"
        assert client.timeout == 30.0
        client.close()

    def test_build_headers_with_api_key(self):
        """Test header building with API key."""
        client = LLMGateway(api_key="test-key", app_id="my-app")
        headers = client._build_headers()
        assert headers["X-API-Key"] == "test-key"
        assert headers["Authorization"] == "Bearer test-key"
        assert headers["X-App-ID"] == "my-app"
        assert headers["Content-Type"] == "application/json"
        client.close()

    def test_build_headers_without_api_key(self):
        """Test header building without API key."""
        client = LLMGateway()
        headers = client._build_headers()
        assert "X-API-Key" not in headers
        assert "Authorization" not in headers
        client.close()

    def test_context_manager(self):
        """Test client as context manager."""
        with LLMGateway() as client:
            assert client is not None

    def test_handle_error_401(self):
        """Test 401 error handling."""
        client = LLMGateway()
        response = MagicMock()
        response.status_code = 401
        response.json.return_value = {"detail": "Invalid credentials"}
        response.text = "Invalid credentials"

        with pytest.raises(AuthenticationError) as exc_info:
            client._handle_error(response)
        assert exc_info.value.status_code == 401
        client.close()

    def test_handle_error_429(self):
        """Test 429 error handling."""
        client = LLMGateway()
        response = MagicMock()
        response.status_code = 429
        response.json.return_value = {"detail": "Rate limit exceeded"}
        response.text = "Rate limit exceeded"
        response.headers = {"Retry-After": "60"}

        with pytest.raises(RateLimitError) as exc_info:
            client._handle_error(response)
        assert exc_info.value.status_code == 429
        assert exc_info.value.retry_after == 60
        client.close()

    def test_handle_error_422(self):
        """Test 422 error handling."""
        client = LLMGateway()
        response = MagicMock()
        response.status_code = 422
        response.json.return_value = {"detail": "Validation error"}
        response.text = "Validation error"

        with pytest.raises(ValidationError) as exc_info:
            client._handle_error(response)
        assert exc_info.value.status_code == 422
        client.close()

    def test_handle_error_500(self):
        """Test 500 error handling."""
        client = LLMGateway()
        response = MagicMock()
        response.status_code = 500
        response.json.return_value = {"detail": "Internal server error"}
        response.text = "Internal server error"

        with pytest.raises(ServerError) as exc_info:
            client._handle_error(response)
        assert exc_info.value.status_code == 500
        client.close()


class TestChatMessage:
    """Tests for ChatMessage model."""

    def test_create_user_message(self):
        """Test creating user message."""
        msg = ChatMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_create_system_message(self):
        """Test creating system message."""
        msg = ChatMessage(role="system", content="You are helpful")
        assert msg.role == "system"
        assert msg.content == "You are helpful"

    def test_create_assistant_message(self):
        """Test creating assistant message."""
        msg = ChatMessage(role="assistant", content="Hi there!")
        assert msg.role == "assistant"


class TestAsyncLLMGatewayClient:
    """Tests for async LLM Gateway client."""

    def test_init(self):
        """Test async client initialization."""
        client = AsyncLLMGateway(
            base_url="https://api.example.com",
            api_key="test-key",
        )
        assert client.base_url == "https://api.example.com"
        assert client.api_key == "test-key"

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test async client as context manager."""
        async with AsyncLLMGateway() as client:
            assert client is not None


class TestExceptions:
    """Tests for exception classes."""

    def test_authentication_error_str(self):
        """Test AuthenticationError string representation."""
        error = AuthenticationError("Invalid key", status_code=401)
        assert str(error) == "[401] Invalid key"

    def test_rate_limit_error_with_retry(self):
        """Test RateLimitError with retry_after."""
        error = RateLimitError("Rate limited", retry_after=60, status_code=429)
        assert error.retry_after == 60
        assert error.status_code == 429

    def test_validation_error(self):
        """Test ValidationError."""
        error = ValidationError(
            "Invalid request",
            status_code=422,
            response_body={"errors": ["field required"]},
        )
        assert error.status_code == 422
        assert error.response_body == {"errors": ["field required"]}
