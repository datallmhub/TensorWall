"""
Models Management API.

CRUD operations for LLM models registry.
Models are stored in the database and can be configured via the admin UI.

Default models are loaded from backend/config/default_models.json (no hardcoded values).
"""

from typing import List, Optional
import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.db.models import LLMModel, ProviderType
from backend.core.jwt import get_current_user_id
from backend.application.providers.ollama import ollama_provider
from backend.application.providers.lmstudio import lmstudio_provider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/models", tags=["Models"])


# === Load default models from external config ===


def _load_default_models() -> list[dict]:
    """Load default models from backend/config/default_models.json."""
    config_paths = [
        Path(__file__).parent.parent.parent
        / "config"
        / "default_models.json",  # backend/config/
        Path(
            "/app/backend/config/default_models.json"
        ),  # Docker path (backend/config/)
        Path.cwd() / "backend" / "config" / "default_models.json",
    ]

    for config_path in config_paths:
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    data = json.load(f)
                    return data.get("models", [])
            except Exception as e:
                logger.warning(f"Failed to load default models from {config_path}: {e}")

    logger.warning("No default_models.json found, seeding will create empty database")
    return []


# === Pydantic Schemas ===


class ModelCreate(BaseModel):
    """Request to create a model."""

    model_id: str
    name: str
    description: Optional[str] = None
    provider: (
        str  # openai, anthropic, ollama, lmstudio, azure_openai, groq, together, custom
    )
    provider_model_id: str
    base_url: Optional[str] = None
    api_key_env_var: Optional[str] = None
    api_key: Optional[str] = None  # Direct API key for cloud providers (OSS)
    context_length: int = 4096
    supports_vision: bool = False
    supports_functions: bool = False
    supports_streaming: bool = True
    input_cost_per_million: float = 0.0
    output_cost_per_million: float = 0.0
    is_enabled: bool = True
    is_default: bool = False
    display_order: int = 100


class ModelUpdate(BaseModel):
    """Request to update a model."""

    name: Optional[str] = None
    description: Optional[str] = None
    base_url: Optional[str] = None
    api_key_env_var: Optional[str] = None
    api_key: Optional[str] = None  # Direct API key for cloud providers (OSS)
    context_length: Optional[int] = None
    supports_vision: Optional[bool] = None
    supports_functions: Optional[bool] = None
    supports_streaming: Optional[bool] = None
    input_cost_per_million: Optional[float] = None
    output_cost_per_million: Optional[float] = None
    is_enabled: Optional[bool] = None
    is_default: Optional[bool] = None
    display_order: Optional[int] = None


class ModelResponse(BaseModel):
    """Model response."""

    id: int
    model_id: str
    name: str
    description: Optional[str]
    provider: str
    provider_model_id: str
    base_url: Optional[str]
    has_api_key: bool = False  # True if api_key is set (never expose the actual key)
    context_length: int
    supports_vision: bool
    supports_functions: bool
    supports_streaming: bool
    input_cost_per_million: float
    output_cost_per_million: float
    is_enabled: bool
    is_default: bool
    display_order: int

    class Config:
        from_attributes = True


class ModelInfo(BaseModel):
    """Simplified model info for playground."""

    id: str
    name: str
    provider: str
    description: Optional[str] = None
    available: bool = True
    context_length: Optional[int] = None
    supports_vision: bool = False
    supports_functions: bool = False


class ProviderStatus(BaseModel):
    """Status of a provider."""

    name: str
    available: bool
    base_url: Optional[str] = None
    model_count: int = 0


class ModelsListResponse(BaseModel):
    """Response with all available models."""

    models: List[ModelInfo]
    providers: List[ProviderStatus]


# === Endpoints ===


@router.get("", response_model=ModelsListResponse)
async def list_models(
    db: AsyncSession = Depends(get_db),
    include_disabled: bool = Query(False, description="Include disabled models"),
):
    """
    List all available models.

    Returns models from the database, grouped by provider.
    Also checks local providers (Ollama, LM Studio) availability.
    """
    # Get models from database
    query = select(LLMModel).order_by(LLMModel.display_order, LLMModel.name)
    if not include_disabled:
        query = query.where(LLMModel.is_enabled.is_(True))

    result = await db.execute(query)
    db_models = result.scalars().all()

    # Convert to response format
    models: List[ModelInfo] = []
    provider_counts: dict = {}

    for m in db_models:
        provider_name = (
            m.provider.value if hasattr(m.provider, "value") else str(m.provider)
        )
        models.append(
            ModelInfo(
                id=m.model_id,
                name=m.name,
                provider=provider_name,
                description=m.description,
                available=m.is_enabled,
                context_length=m.context_length,
                supports_vision=m.supports_vision,
                supports_functions=m.supports_functions,
            )
        )
        provider_counts[provider_name] = provider_counts.get(provider_name, 0) + 1

    # Check local providers
    ollama_available = await ollama_provider.is_available()
    lmstudio_available = await lmstudio_provider.is_available()

    # Get provider base URLs from database
    from backend.core.config import settings

    provider_urls_result = await db.execute(
        select(LLMModel.provider, LLMModel.base_url)
        .distinct()
        .where(LLMModel.is_enabled.is_(True))
    )
    provider_urls: dict[str, str] = {}
    for provider, base_url in provider_urls_result.all():
        provider_name = provider.value if hasattr(provider, "value") else str(provider)
        if base_url and provider_name not in provider_urls:
            provider_urls[provider_name] = base_url

    # Build provider status list (URLs from DB or settings)
    providers = [
        ProviderStatus(
            name="openai",
            available=True,
            base_url=provider_urls.get("openai", settings.openai_api_url),
            model_count=provider_counts.get("openai", 0),
        ),
        ProviderStatus(
            name="anthropic",
            available=True,
            base_url=provider_urls.get("anthropic", settings.anthropic_api_url),
            model_count=provider_counts.get("anthropic", 0),
        ),
        ProviderStatus(
            name="ollama",
            available=ollama_available,
            base_url=ollama_provider.base_url,
            model_count=provider_counts.get("ollama", 0),
        ),
        ProviderStatus(
            name="lmstudio",
            available=lmstudio_available,
            base_url=lmstudio_provider.base_url,
            model_count=provider_counts.get("lmstudio", 0),
        ),
    ]

    return ModelsListResponse(models=models, providers=providers)


def _model_to_response(model: LLMModel) -> ModelResponse:
    """Convert DB model to response, adding has_api_key flag."""
    provider_name = (
        model.provider.value
        if hasattr(model.provider, "value")
        else str(model.provider)
    )
    return ModelResponse(
        id=model.id,
        model_id=model.model_id,
        name=model.name,
        description=model.description,
        provider=provider_name,
        provider_model_id=model.provider_model_id,
        base_url=model.base_url,
        has_api_key=bool(model.api_key),  # True if api_key is set
        context_length=model.context_length,
        supports_vision=model.supports_vision,
        supports_functions=model.supports_functions,
        supports_streaming=model.supports_streaming,
        input_cost_per_million=model.input_cost_per_million,
        output_cost_per_million=model.output_cost_per_million,
        is_enabled=model.is_enabled,
        is_default=model.is_default,
        display_order=model.display_order,
    )


@router.get("/all", response_model=List[ModelResponse])
async def list_all_models(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    List all models (admin view with full details).
    """
    result = await db.execute(
        select(LLMModel).order_by(LLMModel.display_order, LLMModel.name)
    )
    models = result.scalars().all()
    return [_model_to_response(m) for m in models]


@router.post("", response_model=ModelResponse, status_code=status.HTTP_201_CREATED)
async def create_model(
    request: ModelCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Create a new model configuration.
    """
    # Check if model_id already exists
    existing = await db.execute(
        select(LLMModel).where(LLMModel.model_id == request.model_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Model with ID '{request.model_id}' already exists",
        )

    # Validate provider
    try:
        provider = ProviderType(request.provider)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider: {request.provider}. Valid providers: {[p.value for p in ProviderType]}",
        )

    model = LLMModel(
        model_id=request.model_id,
        name=request.name,
        description=request.description,
        provider=provider,
        provider_model_id=request.provider_model_id,
        base_url=request.base_url,
        api_key_env_var=request.api_key_env_var,
        api_key=request.api_key,  # Direct API key for cloud providers (OSS)
        context_length=request.context_length,
        supports_vision=request.supports_vision,
        supports_functions=request.supports_functions,
        supports_streaming=request.supports_streaming,
        input_cost_per_million=request.input_cost_per_million,
        output_cost_per_million=request.output_cost_per_million,
        is_enabled=request.is_enabled,
        is_default=request.is_default,
        display_order=request.display_order,
    )

    db.add(model)
    await db.commit()
    await db.refresh(model)

    return _model_to_response(model)


@router.get("/by-id/{model_id:path}", response_model=ModelResponse)
async def get_model(
    model_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific model configuration."""
    result = await db.execute(select(LLMModel).where(LLMModel.model_id == model_id))
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_id}' not found",
        )

    return _model_to_response(model)


@router.patch("/by-id/{model_id:path}", response_model=ModelResponse)
async def update_model(
    model_id: str,
    request: ModelUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Update a model configuration."""
    result = await db.execute(select(LLMModel).where(LLMModel.model_id == model_id))
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_id}' not found",
        )

    # Update fields
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(model, field, value)

    await db.commit()
    await db.refresh(model)

    return _model_to_response(model)


@router.delete("/by-id/{model_id:path}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(
    model_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Delete a model configuration."""
    result = await db.execute(select(LLMModel).where(LLMModel.model_id == model_id))
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_id}' not found",
        )

    await db.delete(model)
    await db.commit()


@router.post("/by-id/{model_id:path}/enable", response_model=ModelResponse)
async def enable_model(
    model_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Enable a model."""
    result = await db.execute(select(LLMModel).where(LLMModel.model_id == model_id))
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_id}' not found",
        )

    model.is_enabled = True
    await db.commit()
    await db.refresh(model)

    return _model_to_response(model)


@router.post("/by-id/{model_id:path}/disable", response_model=ModelResponse)
async def disable_model(
    model_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Disable a model."""
    result = await db.execute(select(LLMModel).where(LLMModel.model_id == model_id))
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_id}' not found",
        )

    model.is_enabled = False
    await db.commit()
    await db.refresh(model)

    return _model_to_response(model)


@router.post("/seed", response_model=dict)
async def seed_default_models(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Seed the database with default models from config/default_models.json.

    This is useful for initial setup or after clearing the models table.
    Models are loaded from external config file (no hardcoded values).
    """
    # Load models from external config
    default_models = _load_default_models()

    if not default_models:
        return {
            "message": "No default models found in backend/config/default_models.json",
            "created": 0,
            "skipped": 0,
        }

    created = 0
    skipped = 0

    for model_data in default_models:
        # Check if already exists
        existing = await db.execute(
            select(LLMModel).where(LLMModel.model_id == model_data["model_id"])
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue

        # Create model
        try:
            provider = ProviderType(model_data["provider"])
        except ValueError:
            logger.warning(
                f"Unknown provider {model_data['provider']} for model {model_data['model_id']}, skipping"
            )
            skipped += 1
            continue

        model = LLMModel(
            model_id=model_data["model_id"],
            name=model_data["name"],
            description=model_data.get("description"),
            provider=provider,
            provider_model_id=model_data["provider_model_id"],
            base_url=model_data.get("base_url"),
            context_length=model_data.get("context_length", 4096),
            supports_vision=model_data.get("supports_vision", False),
            supports_functions=model_data.get("supports_functions", False),
            input_cost_per_million=model_data.get("input_cost_per_million", 0.0),
            output_cost_per_million=model_data.get("output_cost_per_million", 0.0),
            display_order=model_data.get("display_order", 100),
            is_enabled=model_data.get("is_enabled", True),
        )
        db.add(model)
        created += 1

    await db.commit()

    return {
        "message": f"Seeded {created} models from backend/config/default_models.json, skipped {skipped} existing",
        "created": created,
        "skipped": skipped,
    }


@router.get("/providers/status", response_model=List[ProviderStatus])
async def list_providers(db: AsyncSession = Depends(get_db)):
    """
    List all providers and their availability status.

    Provider URLs are loaded from database models (no hardcoded URLs).
    """
    from backend.core.config import settings

    ollama_available = await ollama_provider.is_available()
    lmstudio_available = await lmstudio_provider.is_available()

    # Get unique providers and their base_urls from database
    result = await db.execute(
        select(LLMModel.provider, LLMModel.base_url)
        .distinct()
        .where(LLMModel.is_enabled.is_(True))
    )
    db_providers = result.all()

    # Build provider URLs from DB
    provider_urls: dict[str, str] = {}
    for provider, base_url in db_providers:
        provider_name = provider.value if hasattr(provider, "value") else str(provider)
        if base_url and provider_name not in provider_urls:
            provider_urls[provider_name] = base_url

    # Use settings for OpenAI/Anthropic if not in DB
    if "openai" not in provider_urls:
        provider_urls["openai"] = settings.openai_api_url
    if "anthropic" not in provider_urls:
        provider_urls["anthropic"] = settings.anthropic_api_url

    return [
        ProviderStatus(
            name="openai", available=True, base_url=provider_urls.get("openai")
        ),
        ProviderStatus(
            name="anthropic", available=True, base_url=provider_urls.get("anthropic")
        ),
        ProviderStatus(
            name="ollama", available=ollama_available, base_url=ollama_provider.base_url
        ),
        ProviderStatus(
            name="lmstudio",
            available=lmstudio_available,
            base_url=lmstudio_provider.base_url,
        ),
        ProviderStatus(name="aws_bedrock", available=True),
        ProviderStatus(name="groq", available=True, base_url=provider_urls.get("groq")),
        ProviderStatus(
            name="mistral", available=True, base_url=provider_urls.get("mistral")
        ),
        ProviderStatus(
            name="google", available=True, base_url=provider_urls.get("google")
        ),
        ProviderStatus(
            name="deepseek", available=True, base_url=provider_urls.get("deepseek")
        ),
    ]


@router.post("/discover/ollama", response_model=dict)
async def discover_ollama_models(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Discover and add models from Ollama.

    Connects to the local Ollama instance and imports available models.
    """
    if not await ollama_provider.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ollama is not running. Start it with 'ollama serve'",
        )

    ollama_models = await ollama_provider.list_models()
    created = 0
    skipped = 0

    for m in ollama_models:
        model_id = f"ollama/{m.name}"

        # Check if exists
        existing = await db.execute(
            select(LLMModel).where(LLMModel.model_id == model_id)
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue

        # Create model
        model = LLMModel(
            model_id=model_id,
            name=m.name.replace(":latest", "").replace("-", " ").title(),
            description="Local model via Ollama",
            provider=ProviderType.OLLAMA,
            provider_model_id=m.name,
            base_url=ollama_provider.base_url,
            context_length=4096,  # Default, can be updated
            is_enabled=True,
            display_order=50,
        )
        db.add(model)
        created += 1

    await db.commit()

    return {
        "message": f"Discovered {created} models from Ollama, skipped {skipped} existing",
        "created": created,
        "skipped": skipped,
    }


@router.post("/discover/lmstudio", response_model=dict)
async def discover_lmstudio_models(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Discover and add models from LM Studio.

    Connects to the local LM Studio instance and imports loaded models.
    """
    if not await lmstudio_provider.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LM Studio is not running. Start it and enable the local server.",
        )

    lmstudio_models = await lmstudio_provider.list_models()
    created = 0
    skipped = 0

    for m in lmstudio_models:
        model_id = f"lmstudio/{m.id}"

        # Check if exists
        existing = await db.execute(
            select(LLMModel).where(LLMModel.model_id == model_id)
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue

        # Create model
        display_name = m.id.split("/")[-1] if "/" in m.id else m.id
        model = LLMModel(
            model_id=model_id,
            name=display_name,
            description="Local model via LM Studio",
            provider=ProviderType.LMSTUDIO,
            provider_model_id=m.id,
            base_url=lmstudio_provider.base_url,
            context_length=4096,  # Default, can be updated
            is_enabled=True,
            display_order=60,
        )
        db.add(model)
        created += 1

    await db.commit()

    return {
        "message": f"Discovered {created} models from LM Studio, skipped {skipped} existing",
        "created": created,
        "skipped": skipped,
    }
