"""Embeddings API v2 - Using Hexagonal Architecture.

Cette version utilise l'architecture hexagonale pour le traitement des requêtes.
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional, Union
import time
import uuid

from backend.core.auth import authenticate, require_auth, AuthResult
from backend.application import (
    EmbeddingCommand,
    EmbeddingOutcome,
    create_embeddings_use_case,
)


router = APIRouter(tags=["Embeddings"])


# =============================================================================
# Request/Response Models
# =============================================================================


class EmbeddingRequestV2(BaseModel):
    model: str
    input: Union[str, list[str]]
    encoding_format: str = "float"


class EmbeddingDataV2(BaseModel):
    object: str = "embedding"
    index: int
    embedding: list[float]


class EmbeddingUsageV2(BaseModel):
    prompt_tokens: int
    total_tokens: int


class EmbeddingResponseV2(BaseModel):
    object: str = "list"
    model: str
    data: list[EmbeddingDataV2]
    usage: EmbeddingUsageV2
    gateway_metadata: Optional[dict] = None


# =============================================================================
# Endpoint
# =============================================================================


@router.post(
    "/embeddings",
    response_model=EmbeddingResponseV2,
    summary="Create embeddings (Hexagonal Architecture)",
    description="""
**Version 2 de l'endpoint embeddings utilisant l'architecture hexagonale.**

Cette version utilise:
- `CreateEmbeddingsUseCase` pour l'orchestration
- `PolicyEvaluator` et `BudgetChecker` (domain layer)
- Ports et Adapters pour l'accès aux données

Pour une version complète, utilisez `/v1/embeddings`.
""",
)
async def create_embeddings_v2(
    request: EmbeddingRequestV2,
    auth_result: AuthResult = Depends(authenticate),
    x_organization_id: Optional[str] = Header(
        None, description="Organization/tenant ID"
    ),
):
    """Create embeddings using hexagonal architecture."""
    start_time = time.time()
    request_id = str(uuid.uuid4())

    # 1. Authentication
    credentials = require_auth(auth_result)

    # 2. Normalize inputs
    inputs = request.input if isinstance(request.input, list) else [request.input]

    # 3. Create use case
    use_case = create_embeddings_use_case(model=request.model)

    # 4. Build command
    command = EmbeddingCommand(
        request_id=request_id,
        app_id=credentials.app_id,
        org_id=x_organization_id or "org_default",
        model=request.model,
        inputs=inputs,
        encoding_format=request.encoding_format,
        api_key=credentials.llm_api_key,
    )

    # 5. Execute use case
    result = await use_case.execute(command)

    latency_ms = int((time.time() - start_time) * 1000)

    # 6. Handle outcome
    if result.outcome == EmbeddingOutcome.DENIED_POLICY:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "request_denied",
                "outcome": result.outcome.value,
                "reason": result.error_message,
                "request_id": request_id,
            },
        )

    if result.outcome == EmbeddingOutcome.DENIED_BUDGET:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "budget_exceeded",
                "outcome": result.outcome.value,
                "reason": result.error_message,
                "request_id": request_id,
            },
        )

    if result.outcome == EmbeddingOutcome.ERROR:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "outcome": result.outcome.value,
                "reason": result.error_message,
                "request_id": request_id,
            },
        )

    # 7. Build response
    response = result.response
    if not response:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "no_response",
                "message": "Use case completed but no response received",
            },
        )

    return EmbeddingResponseV2(
        model=response.model,
        data=[
            EmbeddingDataV2(
                index=emb.index,
                embedding=emb.embedding,
            )
            for emb in response.data
        ],
        usage=EmbeddingUsageV2(
            prompt_tokens=response.total_tokens,
            total_tokens=response.total_tokens,
        ),
        gateway_metadata={
            "request_id": request_id,
            "latency_ms": latency_ms,
            "cost_usd": round(result.cost_usd, 6),
            "architecture": "hexagonal",
        },
    )
