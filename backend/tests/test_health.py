import httpx
import pytest
from fastapi import status

from app.core.config import settings


@pytest.mark.asyncio
async def test_health_liveness_endpoint(async_client: httpx.AsyncClient) -> None:
    """Validate that GET /api/v1/health returns 200 OK and expected environment status."""
    response = await async_client.get("/api/v1/health")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data == {
        "status": "ok",
        "environment": settings.ENVIRONMENT,
    }


@pytest.mark.asyncio
async def test_health_readiness_endpoint_healthy(async_client: httpx.AsyncClient) -> None:
    """Validate that GET /api/v1/health/ready returns 200 OK when database is connected."""
    response = await async_client.get("/api/v1/health/ready")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data == {
        "status": "ready",
        "database": "connected",
    }


@pytest.mark.asyncio
async def test_health_readiness_endpoint_unhealthy(failing_async_client: httpx.AsyncClient) -> None:
    """Validate that GET /api/v1/health/ready returns 503 Service Unavailable when DB fails."""
    response = await failing_async_client.get("/api/v1/health/ready")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Database connection unavailable"


@pytest.mark.asyncio
async def test_application_lifespan() -> None:
    """Validate FastAPI application lifespan startup check and shutdown cleanup."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from app.main import app, lifespan

    mock_engine = MagicMock()
    mock_conn = AsyncMock()
    mock_connect_ctx = AsyncMock()
    mock_connect_ctx.__aenter__.return_value = mock_conn
    mock_connect_ctx.__aexit__.return_value = None
    mock_engine.connect.return_value = mock_connect_ctx
    mock_engine.dispose = AsyncMock()

    with patch("app.main.engine", mock_engine):
        async with lifespan(app):
            pass

        mock_conn.execute.assert_awaited_once()
        mock_engine.dispose.assert_awaited_once()


@pytest.mark.asyncio
async def test_application_lifespan_db_connection_failure() -> None:
    """Validate FastAPI lifespan gracefully handles DB ping error on startup and disposes resources on shutdown."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from app.main import app, lifespan

    mock_engine = MagicMock()
    mock_engine.connect.side_effect = ConnectionRefusedError("Simulated DB connection refused")
    mock_engine.dispose = AsyncMock()

    with patch("app.main.engine", mock_engine):
        async with lifespan(app):
            pass

        mock_engine.dispose.assert_awaited_once()
