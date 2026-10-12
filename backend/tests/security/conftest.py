"""Fixtures for multi-tenancy and security hardening integration tests."""

from collections.abc import AsyncGenerator
import uuid

import httpx
from httpx import ASGITransport
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import get_db_session
from app.core.security import create_access_token, hash_password
from app.main import app
from app.modules.identity.models import PlayerProfile, Role, User
from app.modules.identity.seed import seed_identity_defaults
from app.modules.operators.models import Operator

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


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an asynchronous database session with seeded identity roles and permissions."""
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
async def operator_a(db_session: AsyncSession) -> AsyncGenerator[Operator, None]:
    """Create test Operator A."""
    slug = f"op-a-{uuid.uuid4().hex[:8]}"
    op = Operator(
        name=f"Operator Alpha {slug}",
        slug=slug,
        is_active=True,
    )
    db_session.add(op)
    await db_session.commit()
    await db_session.refresh(op)

    yield op

    await db_session.delete(op)
    await db_session.commit()


@pytest_asyncio.fixture
async def operator_b(db_session: AsyncSession) -> AsyncGenerator[Operator, None]:
    """Create test Operator B."""
    slug = f"op-b-{uuid.uuid4().hex[:8]}"
    op = Operator(
        name=f"Operator Beta {slug}",
        slug=slug,
        is_active=True,
    )
    db_session.add(op)
    await db_session.commit()
    await db_session.refresh(op)

    yield op

    await db_session.delete(op)
    await db_session.commit()


async def _create_user_with_role(
    db: AsyncSession,
    operator_id: uuid.UUID,
    role_name: str,
    prefix: str,
) -> tuple[User, str, dict[str, str]]:
    """Helper to create a user and generate authenticated JWT headers."""
    stmt_role = select(Role).where(Role.name == role_name).options(selectinload(Role.permissions))
    role = await db.scalar(stmt_role)
    assert role is not None, f"Role {role_name} must exist"

    uid = uuid.uuid4().hex[:8]
    user = User(
        operator_id=operator_id,
        email=f"{prefix}-{uid}@test.casino",
        hashed_password=hash_password("SecureP@ss123"),
        is_active=True,
        is_verified=True,
        roles=[role],
    )
    db.add(user)
    await db.flush()

    profile = PlayerProfile(
        user_id=user.id,
        username=f"{prefix}_{uid}",
        first_name="Test",
        last_name="User",
    )
    db.add(profile)
    await db.commit()

    token = create_access_token(data={"sub": str(user.id), "operator_id": str(operator_id)})
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    return user, token, headers


@pytest_asyncio.fixture
async def player_a(db_session: AsyncSession, operator_a: Operator) -> tuple[User, str, dict[str, str]]:
    """Player belonging to Operator A."""
    return await _create_user_with_role(db_session, operator_a.id, "PLAYER", "player-a")


@pytest_asyncio.fixture
async def player_b(db_session: AsyncSession, operator_b: Operator) -> tuple[User, str, dict[str, str]]:
    """Player belonging to Operator B."""
    return await _create_user_with_role(db_session, operator_b.id, "PLAYER", "player-b")


@pytest_asyncio.fixture
async def admin_a(db_session: AsyncSession, operator_a: Operator) -> tuple[User, str, dict[str, str]]:
    """Operator Admin for Operator A."""
    return await _create_user_with_role(db_session, operator_a.id, "OPERATOR_ADMIN", "admin-a")


@pytest_asyncio.fixture
async def admin_b(db_session: AsyncSession, operator_b: Operator) -> tuple[User, str, dict[str, str]]:
    """Operator Admin for Operator B."""
    return await _create_user_with_role(db_session, operator_b.id, "OPERATOR_ADMIN", "admin-b")


@pytest_asyncio.fixture
async def super_admin(db_session: AsyncSession, operator_a: Operator) -> tuple[User, str, dict[str, str]]:
    """Super Admin user."""
    return await _create_user_with_role(db_session, operator_a.id, "SUPER_ADMIN", "superadmin")
