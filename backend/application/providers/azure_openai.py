"""
Azure OpenAI Provider

Supports Azure-hosted OpenAI models with:
- Custom deployment names
- Azure AD authentication
- Regional endpoints
"""

from typing import AsyncIterator, Optional
import httpx

from backend.application.providers.base import LLMProvider, ChatRequest, ChatResponse


class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI API provider."""

    name = "azure_openai"

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_version: str = "2024-02-01",
    ):
        """
        Initialize Azure OpenAI provider.

        Args:
            endpoint: Azure OpenAI endpoint (e.g., https://your-resource.openai.azure.com)
            api_version: Azure OpenAI API version
        """
        self.endpoint = endpoint
        self.api_version = api_version

    def supports_model(self, model: str) -> bool:
        """
        Check if model is an Azure deployment.

        Azure uses deployment names, which can be anything.
        We check for common Azure patterns or explicit azure- prefix.
        """
        return (
            model.startswith("azure-")
            or model.startswith("gpt-")  # Common Azure deployments
            or "-azure" in model
        )

    def _get_headers(self, api_key: str) -> dict:
        """Get request headers for Azure API."""
        return {
            "api-key": api_key,
            "Content-Type": "application/json",
        }

    def _get_url(self, deployment_name: str, endpoint: str) -> str:
        """Construct Azure OpenAI API URL."""
        # Remove azure- prefix if present
        deployment = deployment_name.replace("azure-", "")
        return (
            f"{endpoint}/openai/deployments/{deployment}"
            f"/chat/completions?api-version={self.api_version}"
        )

    async def chat(
        self,
        request: ChatRequest,
        api_key: str,
        endpoint: Optional[str] = None,
    ) -> ChatResponse:
        """
        Send chat completion request to Azure OpenAI.

        Args:
            request: Chat request
            api_key: Azure OpenAI API key
            endpoint: Optional override for Azure endpoint
        """
        azure_endpoint = endpoint or self.endpoint
        if not azure_endpoint:
            raise ValueError(
                "Azure endpoint required. Set AZURE_OPENAI_ENDPOINT or pass endpoint parameter."
            )

        url = self._get_url(request.model, azure_endpoint)

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                headers=self._get_headers(api_key),
                json={
                    "messages": [m.model_dump() for m in request.messages],
                    "max_tokens": request.max_tokens,
                    "temperature": request.temperature,
                    "stream": False,
                },
            )

            response.raise_for_status()
            data = response.json()

            return ChatResponse(
                id=data["id"],
                model=data.get("model", request.model),
                content=data["choices"][0]["message"]["content"],
                input_tokens=data["usage"]["prompt_tokens"],
                output_tokens=data["usage"]["completion_tokens"],
                finish_reason=data["choices"][0]["finish_reason"],
            )

    async def chat_stream(
        self,
        request: ChatRequest,
        api_key: str,
        endpoint: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Stream chat completion from Azure OpenAI."""
        azure_endpoint = endpoint or self.endpoint
        if not azure_endpoint:
            raise ValueError("Azure endpoint required.")

        url = self._get_url(request.model, azure_endpoint)

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                url,
                headers=self._get_headers(api_key),
                json={
                    "messages": [m.model_dump() for m in request.messages],
                    "max_tokens": request.max_tokens,
                    "temperature": request.temperature,
                    "stream": True,
                },
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        yield data


# Factory function for creating provider with config
def create_azure_provider(
    endpoint: Optional[str] = None,
    api_version: str = "2024-02-01",
) -> AzureOpenAIProvider:
    """Create Azure OpenAI provider with configuration."""
    return AzureOpenAIProvider(endpoint=endpoint, api_version=api_version)


# Default singleton (endpoint must be set via environment or parameter)
azure_openai_provider = AzureOpenAIProvider()
