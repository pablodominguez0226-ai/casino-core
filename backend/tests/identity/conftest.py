from collections.abc import AsyncGenerator
import uuid

from fastapi import Depends
import httpx
from httpx import ASGITransport
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import get_db_session
from app.main import app
from app.modules.identity.dependencies import require_permission
from app.modules.identity.seed import seed_identity_defaults
from app.modules.operators.models import Operator

# Test engine with NullPool prevents asyncpg connections from leaking across pytest-asyncio event loops
test_engine = create_async_engine(
    settings.DATABASE_URL,
    poolclass=NullPool,
)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Register a dedicated test endpoint for RBAC checks if not already registered
if not any(getattr(route, "path", None) == "/api/v1/test/admin-only" for route in app.routes):
    @app.get(
        "/api/v1/test/admin-only",
        dependencies=[Depends(require_permission("system:admin"))],
        tags=["testing"],
    )
    async def admin_only_test_endpoint():
        """Restricted endpoint requiring system:admin privilege for testing."""
        return {"status": "authorized", "message": "Admin access granted"}


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an asynchronous database session for integration tests."""
    async with TestSessionLocal() as session:
        await seed_identity_defaults(session)
        yield session


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Asynchronous HTTP test client using the test database session factory."""
    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        async with TestSessionLocal() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db_session] = override_get_db_session

    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_operator(db_session: AsyncSession) -> AsyncGenerator[Operator, None]:
    """Create a primary test tenant operator and clean up after the test."""
    unique_slug = f"op-{uuid.uuid4().hex[:8]}"
    op = Operator(
        name=f"Test Operator {unique_slug}",
        slug=unique_slug,
        is_active=True,
    )
    db_session.add(op)
    await db_session.commit()
    await db_session.refresh(op)

    yield op

    # Teardown: deleting operator cascades to all related tenant data
    await db_session.delete(op)
    await db_session.commit()


@pytest_asyncio.fixture
async def test_operator_two(db_session: AsyncSession) -> AsyncGenerator[Operator, None]:
    """Create a secondary test tenant operator for multitenancy tests and clean up."""
    unique_slug = f"op2-{uuid.uuid4().hex[:8]}"
    op = Operator(
        name=f"Test Operator Two {unique_slug}",
        slug=unique_slug,
        is_active=True,
    )
    db_session.add(op)
    await db_session.commit()
    await db_session.refresh(op)

    yield op

    # Teardown: deleting operator cascades to all related tenant data
    await db_session.delete(op)
    await db_session.commit()
