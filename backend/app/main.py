import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine
from app.modules.health.router import router as health_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager for startup and shutdown events."""
    logger.info("Initializing %s in [%s] environment...", settings.PROJECT_NAME, settings.ENVIRONMENT)

    # Startup: probe database connectivity
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Initial database connectivity verified successfully.")
    except Exception as exc:
        logger.warning(
            "Initial database connectivity check did not succeed: %s. Application will continue starting.",
            exc,
        )

    yield

    # Shutdown: clean up database engine and connection pools
    logger.info("Shutting down %s, releasing database resources...", settings.PROJECT_NAME)
    await engine.dispose()
    logger.info("Database resources disposed successfully.")


def create_application() -> FastAPI:
    """Application factory configuring routes and lifecycle management."""
    application = FastAPI(
        title=settings.PROJECT_NAME,
        version="0.1.0",
        description="Modular B2B Gaming Management Platform",
        lifespan=lifespan,
    )

    # Register API routers
    application.include_router(health_router, prefix="/api/v1")

    return application


app: FastAPI = create_application()
