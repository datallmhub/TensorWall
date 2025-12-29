"""
Health check endpoints with real dependency verification.

Production-ready health checks for:
- Liveness probe (is the service running?)
- Readiness probe (is the service ready to accept traffic?)
- Detailed health status (which dependencies are healthy?)
"""

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Optional
import logging
import asyncio
from sqlalchemy import text

from backend.adapters.exporters import metrics_exporter
from backend.db.session import engine
from backend.adapters.cache.redis_client import get_redis
from backend.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str


class ComponentHealth(BaseModel):
    status: str  # "healthy", "unhealthy", "degraded"
    latency_ms: Optional[float] = None
    message: Optional[str] = None


class DetailedHealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    environment: str
    components: dict[str, ComponentHealth]
    checks_passed: int
    checks_failed: int


# =============================================================================
# Health Check Functions
# =============================================================================


async def check_database() -> ComponentHealth:
    """Check database connectivity and latency."""
    start = datetime.now(timezone.utc)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        return ComponentHealth(
            status="healthy",
            latency_ms=round(latency, 2),
            message="PostgreSQL connection successful",
        )
    except Exception as e:
        latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        logger.error(f"Database health check failed: {e}")
        return ComponentHealth(
            status="unhealthy",
            latency_ms=round(latency, 2),
            message=f"PostgreSQL connection failed: {str(e)[:100]}",
        )


async def check_redis() -> ComponentHealth:
    """Check Redis connectivity and latency."""
    start = datetime.now(timezone.utc)
    try:
        redis = await get_redis()
        if redis:
            await redis.ping()
            latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            return ComponentHealth(
                status="healthy",
                latency_ms=round(latency, 2),
                message="Redis connection successful",
            )
        else:
            return ComponentHealth(
                status="unhealthy", latency_ms=0, message="Redis client not initialized"
            )
    except Exception as e:
        latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        logger.error(f"Redis health check failed: {e}")
        return ComponentHealth(
            status="unhealthy",
            latency_ms=round(latency, 2),
            message=f"Redis connection failed: {str(e)[:100]}",
        )


def check_memory() -> ComponentHealth:
    """Check memory usage."""
    try:
        import psutil

        memory = psutil.virtual_memory()
        used_percent = memory.percent

        if used_percent > 90:
            status = "unhealthy"
            message = f"Memory usage critical: {used_percent}%"
        elif used_percent > 80:
            status = "degraded"
            message = f"Memory usage high: {used_percent}%"
        else:
            status = "healthy"
            message = f"Memory usage: {used_percent}%"

        return ComponentHealth(status=status, message=message)
    except ImportError:
        return ComponentHealth(
            status="healthy", message="Memory check skipped (psutil not installed)"
        )
    except Exception as e:
        return ComponentHealth(status="degraded", message=f"Memory check failed: {str(e)[:100]}")


def check_disk() -> ComponentHealth:
    """Check disk usage."""
    try:
        import psutil

        disk = psutil.disk_usage("/")
        used_percent = disk.percent

        if used_percent > 95:
            status = "unhealthy"
            message = f"Disk usage critical: {used_percent}%"
        elif used_percent > 85:
            status = "degraded"
            message = f"Disk usage high: {used_percent}%"
        else:
            status = "healthy"
            message = f"Disk usage: {used_percent}%"

        return ComponentHealth(status=status, message=message)
    except ImportError:
        return ComponentHealth(
            status="healthy", message="Disk check skipped (psutil not installed)"
        )
    except Exception as e:
        return ComponentHealth(status="degraded", message=f"Disk check failed: {str(e)[:100]}")


# =============================================================================
# Helper Functions
# =============================================================================


def _build_components_dict(names: list[str], results: list) -> dict[str, ComponentHealth]:
    """Build components dictionary from check results."""
    components = {}
    for name, result in zip(names, results):
        if isinstance(result, Exception):
            components[name] = ComponentHealth(status="unhealthy", message=str(result)[:100])
        else:
            components[name] = result
    return components


def _count_checks(components: dict[str, ComponentHealth]) -> tuple[int, int]:
    """Count passed and failed checks."""
    passed = sum(1 for c in components.values() if c.status in ("healthy", "degraded"))
    failed = sum(1 for c in components.values() if c.status == "unhealthy")
    return passed, failed


def _determine_overall_status(components: dict[str, ComponentHealth], checks_failed: int) -> str:
    """Determine overall health status."""
    if checks_failed > 0:
        # Critical components
        if components.get("database", ComponentHealth(status="healthy")).status == "unhealthy":
            return "unhealthy"
        if components.get("redis", ComponentHealth(status="healthy")).status == "unhealthy":
            return "unhealthy"
        return "degraded"
    if any(c.status == "degraded" for c in components.values()):
        return "degraded"
    return "healthy"


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/health",
    summary="Basic health check",
    description="Simple liveness probe - returns healthy if the service is running.",
    tags=["Health"],
)
async def health_check() -> HealthResponse:
    """Basic liveness probe."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
        version="0.1.0",
    )


@router.get(
    "/health/live",
    summary="Kubernetes liveness probe",
    description="Returns 200 if the service is alive. Use for Kubernetes liveness probe.",
    tags=["Health"],
)
async def liveness_probe():
    """Kubernetes liveness probe - always returns 200 if service is running."""
    return {"status": "alive"}


@router.get(
    "/health/ready",
    summary="Kubernetes readiness probe",
    description="""
Returns 200 if the service is ready to accept traffic.
Checks database and Redis connectivity.
Use for Kubernetes readiness probe.
""",
    tags=["Health"],
)
async def readiness_probe():
    """
    Kubernetes readiness probe.

    Checks critical dependencies:
    - Database connectivity
    - Redis connectivity

    Returns 503 if any critical check fails.
    """
    # Run health checks concurrently
    db_check, redis_check = await asyncio.gather(
        check_database(), check_redis(), return_exceptions=True
    )

    # Handle exceptions
    if isinstance(db_check, Exception):
        db_check = ComponentHealth(status="unhealthy", message=str(db_check))
    if isinstance(redis_check, Exception):
        redis_check = ComponentHealth(status="unhealthy", message=str(redis_check))

    # Determine overall status
    critical_healthy = db_check.status == "healthy" and redis_check.status == "healthy"

    if critical_healthy:
        return JSONResponse(
            status_code=200,
            content={
                "status": "ready",
                "checks": {
                    "database": db_check.model_dump(),
                    "redis": redis_check.model_dump(),
                },
            },
        )
    else:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "checks": {
                    "database": db_check.model_dump(),
                    "redis": redis_check.model_dump(),
                },
            },
        )


@router.get(
    "/health/detailed",
    response_model=DetailedHealthResponse,
    summary="Detailed health status",
    description="""
Returns detailed health status of all components.
Includes latency measurements and detailed messages.
""",
    tags=["Health"],
)
async def detailed_health():
    """
    Detailed health check with all components.

    Checks:
    - Database (PostgreSQL)
    - Cache (Redis)
    - Memory usage
    - Disk usage
    """
    # Run async health checks concurrently
    async_results = await asyncio.gather(check_database(), check_redis(), return_exceptions=True)

    # Run sync checks
    sync_results = [check_memory(), check_disk()]

    # Combine results
    results = list(async_results) + sync_results
    component_names = ["database", "redis", "memory", "disk"]

    # Build components dict
    components = _build_components_dict(component_names, results)
    checks_passed, checks_failed = _count_checks(components)
    overall_status = _determine_overall_status(components, checks_failed)

    return DetailedHealthResponse(
        status=overall_status,
        timestamp=datetime.now(timezone.utc),
        version="0.1.0",
        environment=settings.environment,
        components=components,
        checks_passed=checks_passed,
        checks_failed=checks_failed,
    )


@router.get(
    "/ready",
    summary="Legacy readiness check",
    description="Legacy endpoint - prefer /health/ready for Kubernetes.",
    tags=["Health"],
    deprecated=True,
)
async def legacy_readiness_check():
    """Legacy readiness check - redirects to new endpoint."""
    return await readiness_probe()


@router.get("/metrics", response_class=PlainTextResponse, tags=["Health"])
async def prometheus_metrics() -> str:
    """Expose Prometheus metrics."""
    return metrics_exporter.export()
