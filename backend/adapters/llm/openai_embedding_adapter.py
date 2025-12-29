"""OpenAI Embedding Adapter - Adapter pour les embeddings OpenAI.

Architecture Hexagonale: Adapter qui implémente le Port EmbeddingProviderPort.
"""

import httpx

from backend.ports.embedding_provider import EmbeddingProviderPort
from backend.domain.models import EmbeddingRequest, EmbeddingResponse, EmbeddingData
from backend.core.config import settings


class OpenAIEmbeddingAdapter(EmbeddingProviderPort):
    """Adapter pour les embeddings OpenAI.

    Implémente l'interface EmbeddingProviderPort pour OpenAI.
    """

    def __init__(self):
        self.base_url = settings.openai_api_url

    @property
    def name(self) -> str:
        return "openai"

    def supports_model(self, model: str) -> bool:
        """Vérifie si le modèle est un modèle d'embedding OpenAI."""
        return (
            model.startswith("text-embedding-")
            or model == "text-embedding-ada-002"
            or model == "text-embedding-3-small"
            or model == "text-embedding-3-large"
        )

    async def embed(self, request: EmbeddingRequest, api_key: str) -> EmbeddingResponse:
        """Génère des embeddings via l'API OpenAI."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": request.model,
                    "input": request.input,
                    "encoding_format": request.encoding_format,
                },
            )
            response.raise_for_status()
            data = response.json()

        # Convertir la réponse OpenAI vers le format domain
        embeddings = [
            EmbeddingData(
                index=item["index"],
                embedding=item["embedding"],
            )
            for item in data["data"]
        ]

        return EmbeddingResponse(
            model=data["model"],
            data=embeddings,
            total_tokens=data["usage"]["total_tokens"],
        )


# Singleton
openai_embedding_adapter = OpenAIEmbeddingAdapter()
