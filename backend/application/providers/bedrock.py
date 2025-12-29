"""
AWS Bedrock Provider.

Provides access to LLMs via AWS Bedrock Runtime API.
Supports Claude, Llama, Mistral, and Amazon Nova models.

Authentication:
- Uses boto3 with standard AWS credential chain
- Supports: env vars (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION)
- Supports: IAM roles, instance profiles, SSO

The api_key parameter is ignored - AWS credentials are used instead.
"""

from typing import AsyncIterator
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor

from backend.application.providers.base import LLMProvider, ChatRequest, ChatResponse
from backend.core.config import settings

# Thread pool for running sync boto3 calls
_executor = ThreadPoolExecutor(max_workers=10)


class BedrockProvider(LLMProvider):
    """AWS Bedrock provider using boto3."""

    name = "aws_bedrock"

    def __init__(self):
        self._client = None
        self._region = getattr(settings, "aws_region", None) or "us-east-1"
        self._model_cache: dict[str, str] = {}  # model_id -> provider_model_id

    def _get_client(self):
        """Lazy initialization of boto3 client."""
        if self._client is None:
            try:
                import boto3

                self._client = boto3.client("bedrock-runtime", region_name=self._region)
            except ImportError:
                raise ImportError(
                    "boto3 is required for AWS Bedrock. Install it with: pip install boto3"
                )
        return self._client

    def supports_model(self, model: str) -> bool:
        """Check if model is a Bedrock model (pattern matching only)."""
        # Gateway model IDs like "bedrock/claude-3-5-sonnet"
        if model.startswith("bedrock/"):
            return True
        # Direct Bedrock model IDs contain a dot (e.g., "anthropic.claude-3-5-sonnet-20241022-v2:0")
        if "." in model and any(
            model.startswith(prefix)
            for prefix in ("anthropic.", "meta.", "mistral.", "amazon.", "cohere.", "ai21.")
        ):
            return True
        return False

    async def _get_provider_model_id(self, model: str) -> str:
        """Convert gateway model ID to Bedrock model ID from database."""
        # If it's already a Bedrock model ID (contains dot), return as-is
        if "." in model:
            return model

        # Check cache
        if model in self._model_cache:
            return self._model_cache[model]

        # Lookup in database
        from backend.db.session import get_db_context
        from backend.db.models import LLMModel
        from sqlalchemy import select

        try:
            async with get_db_context() as db:
                result = await db.execute(
                    select(LLMModel.provider_model_id).where(LLMModel.model_id == model)
                )
                provider_model_id = result.scalar_one_or_none()

                if provider_model_id:
                    self._model_cache[model] = provider_model_id
                    return provider_model_id
        except Exception as e:
            # Log warning but continue - database lookup is optional
            import logging

            logging.getLogger(__name__).debug(f"DB lookup failed for model {model}: {e}")

        # Fallback: strip prefix and hope it works
        if model.startswith("bedrock/"):
            return model[8:]
        return model

    def _convert_to_bedrock_format(self, request: ChatRequest, model_id: str) -> dict:
        """
        Convert OpenAI format to Bedrock Converse API format.

        Bedrock Converse API is a unified interface that works across all models.
        """
        # Extract system message if present
        system_messages = []
        conversation_messages = []

        for msg in request.messages:
            if msg.role == "system":
                system_messages.append({"text": msg.content})
            else:
                conversation_messages.append({"role": msg.role, "content": [{"text": msg.content}]})

        body = {
            "modelId": model_id,
            "messages": conversation_messages,
        }

        if system_messages:
            body["system"] = system_messages

        # Inference config
        inference_config = {}
        if request.max_tokens:
            inference_config["maxTokens"] = request.max_tokens
        if request.temperature is not None:
            inference_config["temperature"] = request.temperature

        if inference_config:
            body["inferenceConfig"] = inference_config

        return body

    def _sync_chat(self, request: ChatRequest, model_id: str) -> dict:
        """Synchronous chat call for running in thread pool."""
        client = self._get_client()

        body = self._convert_to_bedrock_format(request, model_id)

        # Use Converse API (unified across all Bedrock models)
        response = client.converse(**body)

        return response

    async def chat(self, request: ChatRequest, api_key: str) -> ChatResponse:
        """
        Send chat completion request to AWS Bedrock.

        Note: api_key is ignored - AWS credentials from environment/IAM are used.
        """
        model_id = await self._get_provider_model_id(request.model)

        # Run boto3 sync call in thread pool
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(_executor, self._sync_chat, request, model_id)

        # Extract content from response
        content = ""
        output = response.get("output", {})
        message = output.get("message", {})
        for block in message.get("content", []):
            if "text" in block:
                content += block["text"]

        # Extract usage
        usage = response.get("usage", {})
        input_tokens = usage.get("inputTokens", 0)
        output_tokens = usage.get("outputTokens", 0)

        # Stop reason
        stop_reason = response.get("stopReason", "end_turn")

        return ChatResponse(
            id=response.get("ResponseMetadata", {}).get("RequestId", "bedrock-response"),
            model=model_id,
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            finish_reason=stop_reason,
        )

    def _sync_stream(self, request: ChatRequest, model_id: str):
        """Synchronous streaming call - yields chunks."""
        client = self._get_client()

        body = self._convert_to_bedrock_format(request, model_id)

        # Use ConverseStream API
        response = client.converse_stream(**body)

        stream = response.get("stream")
        if stream:
            for event in stream:
                if "contentBlockDelta" in event:
                    delta = event["contentBlockDelta"].get("delta", {})
                    if "text" in delta:
                        yield delta["text"]
                elif "messageStop" in event:
                    break

    async def chat_stream(self, request: ChatRequest, api_key: str) -> AsyncIterator[str]:
        """
        Stream chat completion from AWS Bedrock.

        Converts to OpenAI SSE format for compatibility.
        """
        model_id = await self._get_provider_model_id(request.model)

        loop = asyncio.get_event_loop()

        # Run sync generator in thread pool and yield chunks
        def run_stream():
            return list(self._sync_stream(request, model_id))

        chunks = await loop.run_in_executor(_executor, run_stream)

        for text in chunks:
            openai_chunk = {
                "choices": [
                    {
                        "delta": {"content": text},
                        "index": 0,
                    }
                ]
            }
            yield json.dumps(openai_chunk)

    async def is_available(self) -> bool:
        """Check if Bedrock is available (AWS credentials configured)."""
        try:
            import boto3

            # Try to create a client - this will fail if no credentials
            boto3.client("bedrock-runtime", region_name=self._region)
            # If client creation succeeds, credentials are configured
            return True
        except Exception:
            return False


# Singleton
bedrock_provider = BedrockProvider()
