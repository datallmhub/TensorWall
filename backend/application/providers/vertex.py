"""
Google Vertex AI Provider

Supports Google Cloud's Vertex AI with:
- Gemini models (gemini-pro, gemini-ultra)
- PaLM models (text-bison, chat-bison)
- Claude models (via Model Garden)

Requires:
- Google Cloud project ID
- Service account or ADC authentication
"""

from typing import AsyncIterator, Optional
import httpx
import json

from backend.application.providers.base import LLMProvider, ChatRequest, ChatResponse


class VertexAIProvider(LLMProvider):
    """Google Vertex AI provider."""

    name = "vertex_ai"

    # Model mapping to Vertex AI endpoints
    MODEL_ENDPOINTS = {
        "gemini-pro": "gemini-1.0-pro",
        "gemini-1.0-pro": "gemini-1.0-pro",
        "gemini-1.5-pro": "gemini-1.5-pro-001",
        "gemini-1.5-flash": "gemini-1.5-flash-001",
        "gemini-ultra": "gemini-1.0-ultra",
        "gemini-2.0-flash": "gemini-2.0-flash-exp",
    }

    def __init__(
        self,
        project_id: Optional[str] = None,
        location: str = "us-central1",
    ):
        """
        Initialize Vertex AI provider.

        Args:
            project_id: Google Cloud project ID
            location: Vertex AI region (default: us-central1)
        """
        self.project_id = project_id
        self.location = location

    def supports_model(self, model: str) -> bool:
        """Check if model is supported by Vertex AI."""
        return (
            model.startswith("gemini")
            or model.startswith("palm")
            or model.startswith("text-bison")
            or model.startswith("chat-bison")
            or model in self.MODEL_ENDPOINTS
        )

    def _get_model_id(self, model: str) -> str:
        """Get Vertex AI model ID from model name."""
        return self.MODEL_ENDPOINTS.get(model, model)

    def _get_url(self, model: str, project_id: str, stream: bool = False) -> str:
        """Construct Vertex AI API URL."""
        model_id = self._get_model_id(model)
        action = "streamGenerateContent" if stream else "generateContent"
        return (
            f"https://{self.location}-aiplatform.googleapis.com/v1/"
            f"projects/{project_id}/locations/{self.location}/"
            f"publishers/google/models/{model_id}:{action}"
        )

    def _convert_messages(self, messages: list) -> dict:
        """Convert OpenAI message format to Vertex AI format."""
        contents = []
        system_instruction = None

        for msg in messages:
            role = msg.role if hasattr(msg, "role") else msg.get("role")
            content = msg.content if hasattr(msg, "content") else msg.get("content")

            if role == "system":
                system_instruction = {"parts": [{"text": content}]}
            else:
                # Map OpenAI roles to Vertex AI roles
                vertex_role = "user" if role == "user" else "model"
                contents.append({"role": vertex_role, "parts": [{"text": content}]})

        result = {"contents": contents}
        if system_instruction:
            result["systemInstruction"] = system_instruction

        return result

    async def chat(
        self,
        request: ChatRequest,
        api_key: str,
        project_id: Optional[str] = None,
    ) -> ChatResponse:
        """
        Send chat completion request to Vertex AI.

        Args:
            request: Chat request
            api_key: Google Cloud access token (from gcloud auth print-access-token)
            project_id: Optional override for project ID
        """
        gcp_project = project_id or self.project_id
        if not gcp_project:
            raise ValueError(
                "Google Cloud project ID required. "
                "Set GOOGLE_CLOUD_PROJECT or pass project_id parameter."
            )

        url = self._get_url(request.model, gcp_project, stream=False)
        body = self._convert_messages(request.messages)

        # Add generation config
        body["generationConfig"] = {
            "maxOutputTokens": request.max_tokens or 2048,
            "temperature": request.temperature or 0.7,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
            )

            response.raise_for_status()
            data = response.json()

            # Parse Vertex AI response
            candidate = data["candidates"][0]
            content = candidate["content"]["parts"][0]["text"]

            # Extract usage metadata
            usage = data.get("usageMetadata", {})

            return ChatResponse(
                id=f"vertex-{hash(content) % 10**8}",
                model=request.model,
                content=content,
                input_tokens=usage.get("promptTokenCount", 0),
                output_tokens=usage.get("candidatesTokenCount", 0),
                finish_reason=candidate.get("finishReason", "stop").lower(),
            )

    async def chat_stream(
        self,
        request: ChatRequest,
        api_key: str,
        project_id: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Stream chat completion from Vertex AI."""
        gcp_project = project_id or self.project_id
        if not gcp_project:
            raise ValueError("Google Cloud project ID required.")

        url = self._get_url(request.model, gcp_project, stream=True)
        body = self._convert_messages(request.messages)
        body["generationConfig"] = {
            "maxOutputTokens": request.max_tokens or 2048,
            "temperature": request.temperature or 0.7,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            # Vertex AI streams JSON objects
                            data = json.loads(line)
                            if "candidates" in data:
                                content = data["candidates"][0]["content"]["parts"][
                                    0
                                ].get("text", "")
                                if content:
                                    # Convert to OpenAI SSE format
                                    yield json.dumps(
                                        {
                                            "choices": [
                                                {
                                                    "delta": {"content": content},
                                                    "index": 0,
                                                }
                                            ]
                                        }
                                    )
                        except json.JSONDecodeError:
                            continue


# Factory function
def create_vertex_provider(
    project_id: Optional[str] = None,
    location: str = "us-central1",
) -> VertexAIProvider:
    """Create Vertex AI provider with configuration."""
    return VertexAIProvider(project_id=project_id, location=location)


# Default singleton
vertex_ai_provider = VertexAIProvider()
