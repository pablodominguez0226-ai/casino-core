"""Fixtures for reports module tests."""
from collections.abc import AsyncGenerator
from datetime import timedelta
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
    """Provide an asynchronous database session for reporting integration tests."""
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
    """Create a primary tenant operator for reports tests."""
    slug = f"rep-op-{uuid.uuid4().hex[:8]}"
    op = Operator(
        name=f"Reports Operator {slug}",
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
async def test_operator_b(db_session: AsyncSession) -> AsyncGenerator[Operator, None]:
    """Create a secondary tenant operator for multitenancy tests."""
    slug = f"rep-opb-{uuid.uuid4().hex[:8]}"
    op = Operator(
        name=f"Reports Operator B {slug}",
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
    email_prefix: str,
) -> User:
    stmt_role = select(Role).where(Role.name == role_name).options(selectinload(Role.permissions))
    role = await db.scalar(stmt_role)
    assert role is not None, f"Role {role_name} should exist"

    user = User(
        operator_id=operator_id,
        email=f"{email_prefix}-{uuid.uuid4().hex[:8]}@casino.com",
        hashed_password=hash_password("SecurePassword123!"),
        is_active=True,
        is_verified=True,
        roles=[role],
    )
    profile = PlayerProfile(
        user=user,
        username=f"u_{uuid.uuid4().hex[:8]}",
    )
    db.add(user)
    db.add(profile)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def player_user(db_session: AsyncSession, test_operator: Operator) -> User:
    return await _create_user_with_role(db_session, test_operator.id, "PLAYER", "player")


@pytest_asyncio.fixture
async def operator_admin_user(db_session: AsyncSession, test_operator: Operator) -> User:
    return await _create_user_with_role(db_session, test_operator.id, "OPERATOR_ADMIN", "op-admin")


@pytest_asyncio.fixture
async def finance_user(db_session: AsyncSession, test_operator: Operator) -> User:
    return await _create_user_with_role(db_session, test_operator.id, "FINANCE", "finance")


@pytest_asyncio.fixture
async def game_manager_user(db_session: AsyncSession, test_operator: Operator) -> User:
    return await _create_user_with_role(db_session, test_operator.id, "GAME_MANAGER", "gamemgr")


@pytest_asyncio.fixture
async def super_admin_user(db_session: AsyncSession, test_operator: Operator) -> User:
    return await _create_user_with_role(db_session, test_operator.id, "SUPER_ADMIN", "superadmin")


@pytest_asyncio.fixture
def player_headers(player_user: User) -> dict[str, str]:
    token = create_access_token(data={"sub": str(player_user.id)}, expires_delta=timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
def operator_admin_headers(operator_admin_user: User) -> dict[str, str]:
    token = create_access_token(data={"sub": str(operator_admin_user.id)}, expires_delta=timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
def finance_headers(finance_user: User) -> dict[str, str]:
    token = create_access_token(data={"sub": str(finance_user.id)}, expires_delta=timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
def game_manager_headers(game_manager_user: User) -> dict[str, str]:
    token = create_access_token(data={"sub": str(game_manager_user.id)}, expires_delta=timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
def super_admin_headers(super_admin_user: User) -> dict[str, str]:
    token = create_access_token(data={"sub": str(super_admin_user.id)}, expires_delta=timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}
