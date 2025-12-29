"""LLM Gateway SDK client implementations."""

from typing import Optional, Dict, Any, List, Iterator, AsyncIterator, Union
import httpx
import json

from llm_gateway_sdk.models import (
    ChatMessage,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChunk,
    EmbeddingRequest,
    EmbeddingResponse,
)
from llm_gateway_sdk.exceptions import (
    LLMGatewayError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
    ServerError,
    PolicyDeniedError,
    BudgetExceededError,
)


class _BaseClient:
    """Base client with shared functionality."""

    DEFAULT_BASE_URL = "http://localhost:8000"
    DEFAULT_TIMEOUT = 60.0

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        app_id: Optional[str] = None,
        org_id: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        headers: Optional[Dict[str, str]] = None,
    ):
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.api_key = api_key
        self.app_id = app_id
        self.org_id = org_id
        self.timeout = timeout
        self._custom_headers = headers or {}

    def _build_headers(self) -> Dict[str, str]:
        """Build request headers."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            **self._custom_headers,
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key
            headers["Authorization"] = f"Bearer {self.api_key}"
        if self.app_id:
            headers["X-App-ID"] = self.app_id
        if self.org_id:
            headers["X-Org-ID"] = self.org_id
        return headers

    def _handle_error(self, response: httpx.Response) -> None:
        """Handle HTTP error responses."""
        try:
            body = response.json()
        except Exception:
            body = {"detail": response.text}

        message = body.get("detail", body.get("message", "Unknown error"))
        status_code = response.status_code

        # Check for specific error types
        error_code = body.get("error_code", "")

        if status_code == 401 or status_code == 403:
            raise AuthenticationError(message, status_code, body)
        elif status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(
                message,
                retry_after=int(retry_after) if retry_after else None,
                status_code=status_code,
                response_body=body,
            )
        elif status_code in (400, 422):
            raise ValidationError(message, status_code, body)
        elif status_code >= 500:
            raise ServerError(message, status_code, body)
        elif "policy" in error_code.lower() or "policy" in message.lower():
            raise PolicyDeniedError(
                message,
                policy_name=body.get("policy_name"),
                status_code=status_code,
                response_body=body,
            )
        elif "budget" in error_code.lower() or "budget" in message.lower():
            raise BudgetExceededError(
                message,
                budget_type=body.get("budget_type"),
                limit=body.get("limit"),
                current=body.get("current"),
                status_code=status_code,
                response_body=body,
            )
        else:
            raise LLMGatewayError(message, status_code, body)


class LLMGateway(_BaseClient):
    """Synchronous LLM Gateway client."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        app_id: Optional[str] = None,
        org_id: Optional[str] = None,
        timeout: float = _BaseClient.DEFAULT_TIMEOUT,
        headers: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize LLM Gateway client.

        Args:
            base_url: Base URL of the LLM Gateway server (default: http://localhost:8000)
            api_key: API key for authentication
            app_id: Application ID for request tracking
            org_id: Organization ID for multi-tenancy
            timeout: Request timeout in seconds (default: 60)
            headers: Additional headers to include in requests
        """
        super().__init__(base_url, api_key, app_id, org_id, timeout, headers)
        self._client = httpx.Client(timeout=timeout)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self) -> None:
        """Close the client."""
        self._client.close()

    def chat(
        self,
        messages: List[Union[ChatMessage, Dict[str, Any]]],
        model: str = "gpt-4",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs,
    ) -> Union[ChatCompletionResponse, Iterator[ChatCompletionChunk]]:
        """
        Create a chat completion.

        Args:
            messages: List of messages in the conversation
            model: Model to use (default: gpt-4)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            **kwargs: Additional parameters (top_p, stop, tools, etc.)

        Returns:
            ChatCompletionResponse or Iterator of ChatCompletionChunk if streaming
        """
        # Convert dicts to ChatMessage
        chat_messages = [
            m if isinstance(m, ChatMessage) else ChatMessage(**m)
            for m in messages
        ]

        request = ChatCompletionRequest(
            model=model,
            messages=chat_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
            app_id=kwargs.pop("app_id", self.app_id),
            **kwargs,
        )

        if stream:
            return self._stream_chat(request)
        return self._chat(request)

    def _chat(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """Execute non-streaming chat request."""
        response = self._client.post(
            f"{self.base_url}/v1/chat/completions",
            headers=self._build_headers(),
            json=request.model_dump(exclude_none=True),
        )

        if response.status_code >= 400:
            self._handle_error(response)

        return ChatCompletionResponse(**response.json())

    def _stream_chat(
        self, request: ChatCompletionRequest
    ) -> Iterator[ChatCompletionChunk]:
        """Execute streaming chat request."""
        headers = self._build_headers()
        headers["Accept"] = "text/event-stream"

        with self._client.stream(
            "POST",
            f"{self.base_url}/v1/chat/completions",
            headers=headers,
            json=request.model_dump(exclude_none=True),
        ) as response:
            if response.status_code >= 400:
                response.read()
                self._handle_error(response)

            for line in response.iter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        yield ChatCompletionChunk(**chunk)
                    except json.JSONDecodeError:
                        continue

    def embeddings(
        self,
        input: Union[str, List[str]],
        model: str = "text-embedding-ada-002",
        **kwargs,
    ) -> EmbeddingResponse:
        """
        Create embeddings.

        Args:
            input: Text or list of texts to embed
            model: Embedding model to use
            **kwargs: Additional parameters

        Returns:
            EmbeddingResponse with embedding vectors
        """
        request = EmbeddingRequest(
            model=model,
            input=input,
            app_id=kwargs.pop("app_id", self.app_id),
            **kwargs,
        )

        response = self._client.post(
            f"{self.base_url}/v1/embeddings",
            headers=self._build_headers(),
            json=request.model_dump(exclude_none=True),
        )

        if response.status_code >= 400:
            self._handle_error(response)

        return EmbeddingResponse(**response.json())

    def health(self) -> Dict[str, Any]:
        """Check gateway health."""
        response = self._client.get(f"{self.base_url}/health")
        return response.json()

    def models(self) -> List[Dict[str, Any]]:
        """List available models."""
        response = self._client.get(
            f"{self.base_url}/v1/models",
            headers=self._build_headers(),
        )
        if response.status_code >= 400:
            self._handle_error(response)
        return response.json().get("data", [])


class AsyncLLMGateway(_BaseClient):
    """Asynchronous LLM Gateway client."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        app_id: Optional[str] = None,
        org_id: Optional[str] = None,
        timeout: float = _BaseClient.DEFAULT_TIMEOUT,
        headers: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize async LLM Gateway client.

        Args:
            base_url: Base URL of the LLM Gateway server
            api_key: API key for authentication
            app_id: Application ID for request tracking
            org_id: Organization ID for multi-tenancy
            timeout: Request timeout in seconds
            headers: Additional headers to include in requests
        """
        super().__init__(base_url, api_key, app_id, org_id, timeout, headers)
        self._client = httpx.AsyncClient(timeout=timeout)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def close(self) -> None:
        """Close the client."""
        await self._client.aclose()

    async def chat(
        self,
        messages: List[Union[ChatMessage, Dict[str, Any]]],
        model: str = "gpt-4",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs,
    ) -> Union[ChatCompletionResponse, AsyncIterator[ChatCompletionChunk]]:
        """
        Create a chat completion asynchronously.

        Args:
            messages: List of messages in the conversation
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            **kwargs: Additional parameters

        Returns:
            ChatCompletionResponse or AsyncIterator of ChatCompletionChunk
        """
        chat_messages = [
            m if isinstance(m, ChatMessage) else ChatMessage(**m)
            for m in messages
        ]

        request = ChatCompletionRequest(
            model=model,
            messages=chat_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
            app_id=kwargs.pop("app_id", self.app_id),
            **kwargs,
        )

        if stream:
            return self._stream_chat(request)
        return await self._chat(request)

    async def _chat(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """Execute non-streaming chat request."""
        response = await self._client.post(
            f"{self.base_url}/v1/chat/completions",
            headers=self._build_headers(),
            json=request.model_dump(exclude_none=True),
        )

        if response.status_code >= 400:
            self._handle_error(response)

        return ChatCompletionResponse(**response.json())

    async def _stream_chat(
        self, request: ChatCompletionRequest
    ) -> AsyncIterator[ChatCompletionChunk]:
        """Execute streaming chat request."""
        headers = self._build_headers()
        headers["Accept"] = "text/event-stream"

        async with self._client.stream(
            "POST",
            f"{self.base_url}/v1/chat/completions",
            headers=headers,
            json=request.model_dump(exclude_none=True),
        ) as response:
            if response.status_code >= 400:
                await response.aread()
                self._handle_error(response)

            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        yield ChatCompletionChunk(**chunk)
                    except json.JSONDecodeError:
                        continue

    async def embeddings(
        self,
        input: Union[str, List[str]],
        model: str = "text-embedding-ada-002",
        **kwargs,
    ) -> EmbeddingResponse:
        """
        Create embeddings asynchronously.

        Args:
            input: Text or list of texts to embed
            model: Embedding model to use
            **kwargs: Additional parameters

        Returns:
            EmbeddingResponse with embedding vectors
        """
        request = EmbeddingRequest(
            model=model,
            input=input,
            app_id=kwargs.pop("app_id", self.app_id),
            **kwargs,
        )

        response = await self._client.post(
            f"{self.base_url}/v1/embeddings",
            headers=self._build_headers(),
            json=request.model_dump(exclude_none=True),
        )

        if response.status_code >= 400:
            self._handle_error(response)

        return EmbeddingResponse(**response.json())

    async def health(self) -> Dict[str, Any]:
        """Check gateway health."""
        response = await self._client.get(f"{self.base_url}/health")
        return response.json()

    async def models(self) -> List[Dict[str, Any]]:
        """List available models."""
        response = await self._client.get(
            f"{self.base_url}/v1/models",
            headers=self._build_headers(),
        )
        if response.status_code >= 400:
            self._handle_error(response)
        return response.json().get("data", [])
