import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.modules.health.schemas import HealthReadyResponse, HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness check",
    description="Returns service status and current active environment.",
)
async def get_health() -> HealthResponse:
    """Return application liveness status."""
    return HealthResponse(
        status="ok",
        environment=settings.ENVIRONMENT,
    )


@router.get(
    "/ready",
    response_model=HealthReadyResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness check",
    description="Verifies database connectivity by executing a lightweight ping query.",
)
async def get_health_ready(
    session: AsyncSession = Depends(get_db_session),
) -> HealthReadyResponse:
    """Verify application readiness and database connectivity."""
    try:
        result = await session.execute(text("SELECT 1"))
        result.scalar_one()
        return HealthReadyResponse(
            status="ready",
            database="connected",
        )
    except Exception as exc:
        logger.error("Readiness probe database connection failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable",
        ) from exc
