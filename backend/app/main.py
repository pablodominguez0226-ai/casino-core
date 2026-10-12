from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine
from app.core.telemetry.logging import setup_telemetry_logging
from app.core.telemetry.metrics import router as metrics_router
from app.core.telemetry.middleware import TelemetryMiddleware
from app.core.tenant.middleware import TenantMiddleware
from app.modules.audit.router import router as audit_router
from app.modules.gaming.router import router as gaming_router, rounds_router
from app.modules.health.router import router as health_router
from app.modules.identity.router import router as identity_router
from app.modules.operators.router import (
    admin_router as operators_admin_router,
    router as operators_router,
)
from app.modules.reports.router import router as reports_router
from app.modules.responsible.router import router as responsible_router
from app.modules.wallet.router import router as wallet_router

# Configure structured JSON logging for production and non-development environments
if settings.ENVIRONMENT != "development":
    setup_telemetry_logging(settings.LOG_LEVEL)

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

    # Register telemetry and observability middleware (outer) and tenant middleware (inner)
    application.add_middleware(TenantMiddleware)
    application.add_middleware(TelemetryMiddleware)

    # Register API routers
    application.include_router(health_router, prefix="/api/v1")
    application.include_router(identity_router, prefix="/api/v1")
    application.include_router(operators_admin_router, prefix="/api/v1")
    application.include_router(operators_router, prefix="/api/v1")
    application.include_router(wallet_router, prefix="/api/v1")
    application.include_router(gaming_router, prefix="/api/v1")
    application.include_router(rounds_router, prefix="/api/v1")
    application.include_router(audit_router, prefix="/api/v1")
    application.include_router(reports_router, prefix="/api/v1")
    application.include_router(responsible_router, prefix="/api/v1")
    application.include_router(metrics_router, prefix="/api/v1")

    return application


app: FastAPI = create_application()
