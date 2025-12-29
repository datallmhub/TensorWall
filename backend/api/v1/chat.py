"""Chat Completions API v2 - Using Hexagonal Architecture.

Cette version utilise l'architecture hexagonale pour le traitement des requêtes.
C'est une version simplifiée qui sera progressivement enrichie pour atteindre
la parité avec chat.py.

Migration progressive:
- Phase 1: ✅ Domain Layer
- Phase 2: ✅ Ports Layer
- Phase 3: ✅ Adapters Layer
- Phase 4: ✅ Application Layer
- Phase 5: ✅ API Integration (ce fichier)

Fonctionnalités:
- ✅ Policy evaluation
- ✅ Budget checking
- ✅ LLM call (sync et streaming)
- ✅ Dry-run mode
- ✅ Metrics (via MetricsPort)
- ⏳ Abuse detection (non implémenté)
- ⏳ Feature allowlisting (non implémenté)
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import time
import uuid

from backend.core.auth import authenticate, require_auth, AuthResult
from backend.application import (
    LLMRequestCommand,
    LLMRequestResult,
    RequestOutcome,
    create_evaluate_llm_request_use_case,
)
from backend.application.engines.security import security_guard


router = APIRouter(tags=["Chat"])


# =============================================================================
# Request/Response Models
# =============================================================================


class ChatCompletionMessageV2(BaseModel):
    role: str
    content: str


class ChatCompletionRequestV2(BaseModel):
    model: str
    messages: list[ChatCompletionMessageV2]
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    stream: bool = False
    feature_id: Optional[str] = None


class ChatCompletionChoiceV2(BaseModel):
    index: int
    message: ChatCompletionMessageV2
    finish_reason: str


class ChatCompletionUsageV2(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponseV2(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoiceV2]
    usage: ChatCompletionUsageV2
    gateway_metadata: Optional[dict] = None


# =============================================================================
# Endpoint (Hexagonal Architecture)
# =============================================================================


@router.post(
    "/chat/completions",
    response_model=None,  # Dynamic: ChatCompletionResponseV2 or StreamingResponse
    summary="Chat completion",
    description="""
**Endpoint chat utilisant l'architecture hexagonale.**

Cette version utilise:
- `EvaluateLLMRequestUseCase` pour l'orchestration
- `PolicyEvaluator` et `BudgetChecker` (domain layer)
- Ports et Adapters pour l'accès aux données
- Streaming support via `execute_stream()`
- Metrics via `MetricsPort`

Fonctionnalités supportées:
- ✅ Policy evaluation
- ✅ Budget checking
- ✅ LLM call (sync et streaming)
- ✅ Dry-run mode
- ✅ Metrics

Limitations:
- Pas d'abuse detection
- Pas de feature allowlisting

Pour une version complète, utilisez `/v1/chat/completions`.
""",
)
async def chat_completions_v2(
    request: ChatCompletionRequestV2,
    auth_result: AuthResult = Depends(authenticate),
    x_organization_id: Optional[str] = Header(None, description="Organization/tenant ID"),
    x_feature_id: Optional[str] = Header(None, description="Feature/use-case identifier"),
    x_dry_run: Optional[str] = Header(None, description="Set to 'true' for dry-run"),
):
    """Chat completion endpoint using hexagonal architecture."""
    start_time = time.time()
    request_id = str(uuid.uuid4())
    is_dry_run = x_dry_run == "true"

    # 1. Authentication
    credentials = require_auth(auth_result)

    # 2. Create use case with metrics enabled
    use_case = create_evaluate_llm_request_use_case(
        model=request.model,
        enable_metrics=True,
    )

    # 3. Run security analysis (OSS: always visible in response)
    messages_for_security = [{"role": m.role, "content": m.content} for m in request.messages]
    security_result = security_guard.full_analysis(messages_for_security)

    # 4. Build command
    command = LLMRequestCommand(
        request_id=request_id,
        app_id=credentials.app_id,
        org_id=x_organization_id or "org_default",
        model=request.model,
        messages=messages_for_security,
        environment="development",  # TODO: extract from contract
        feature=request.feature_id or x_feature_id,
        max_tokens=request.max_tokens,
        temperature=request.temperature,
        stream=request.stream,
        dry_run=is_dry_run,
        api_key=credentials.llm_api_key,
    )

    # 5. Handle streaming mode
    if request.stream:
        result = await use_case.execute_stream(command)

        # Check if it's a denial/error result
        if isinstance(result, LLMRequestResult):
            return _handle_result_error(result, request_id)

        # Return streaming response
        async def stream_generator():
            try:
                async for chunk in result:
                    yield f"data: {chunk}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                yield f'data: {{"error": "{str(e)}"}}\n\n'

        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
            headers={
                "X-Request-Id": request_id,
                "Cache-Control": "no-cache",
            },
        )

    # 6. Execute use case (non-streaming)
    result = await use_case.execute(command)

    latency_ms = int((time.time() - start_time) * 1000)

    # 7. Handle errors
    error_response = _handle_result_error(result, request_id)
    if error_response:
        raise error_response

    # 8. Handle dry-run
    if result.outcome == RequestOutcome.DRY_RUN:
        return {
            "dry_run": True,
            "request_id": request_id,
            "would_be_allowed": result.dry_run_result.get("would_be_allowed", False),
            "policy_action": result.dry_run_result.get("policy_action"),
            "estimated_cost_usd": result.dry_run_result.get("estimated_cost_usd"),
            "budget_remaining_usd": result.dry_run_result.get("budget_remaining_usd"),
            "budget_usage_percent": result.dry_run_result.get("budget_usage_percent"),
            "security": security_result.to_api_response(),
        }

    # 9. Build response
    response = result.response
    if not response:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "no_response",
                "message": "Use case completed but no response received",
            },
        )

    return ChatCompletionResponseV2(
        id=response.id,
        created=int(time.time()),
        model=response.model,
        choices=[
            ChatCompletionChoiceV2(
                index=0,
                message=ChatCompletionMessageV2(role="assistant", content=response.content),
                finish_reason=response.finish_reason or "stop",
            )
        ],
        usage=ChatCompletionUsageV2(
            prompt_tokens=response.input_tokens,
            completion_tokens=response.output_tokens,
            total_tokens=response.input_tokens + response.output_tokens,
        ),
        gateway_metadata={
            "request_id": request_id,
            "latency_ms": latency_ms,
            "security": security_result.to_api_response(),
        },
    )


def _handle_result_error(result: LLMRequestResult, request_id: str) -> HTTPException | None:
    """Convert use case result errors to HTTP exceptions."""
    if result.outcome == RequestOutcome.DENIED_POLICY:
        return HTTPException(
            status_code=403,
            detail={
                "error": "request_denied",
                "outcome": result.outcome.value,
                "reason": result.error_message,
                "request_id": request_id,
            },
        )

    if result.outcome == RequestOutcome.DENIED_BUDGET:
        return HTTPException(
            status_code=429,
            detail={
                "error": "budget_exceeded",
                "outcome": result.outcome.value,
                "reason": result.error_message,
                "request_id": request_id,
            },
        )

    if result.outcome == RequestOutcome.ERROR:
        return HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "outcome": result.outcome.value,
                "reason": result.error_message,
                "request_id": request_id,
            },
        )

    return None
