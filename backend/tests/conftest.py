from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import httpx
from httpx import ASGITransport
import pytest
import pytest_asyncio

from app.core.database import get_db_session
from app.main import app


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Mock asynchronous SQLAlchemy session that resolves SELECT 1 successfully."""
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 1
    session.execute.return_value = mock_result
    return session


@pytest_asyncio.fixture
async def async_client(mock_db_session: AsyncMock) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Asynchronous HTTP test client with database dependency mocked by default."""
    async def override_get_db_session() -> AsyncGenerator[AsyncMock, None]:
        yield mock_db_session

    app.dependency_overrides[get_db_session] = override_get_db_session

    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def failing_async_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Asynchronous HTTP test client configured with a failing database connection."""
    failing_session = AsyncMock()
    failing_session.execute.side_effect = ConnectionRefusedError("Database connection refused")

    async def override_failing_get_db_session() -> AsyncGenerator[AsyncMock, None]:
        yield failing_session

    app.dependency_overrides[get_db_session] = override_failing_get_db_session

    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()
