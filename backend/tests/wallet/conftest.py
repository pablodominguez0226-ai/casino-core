from collections.abc import AsyncGenerator
from datetime import timedelta
import uuid

import httpx
from httpx import ASGITransport
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import get_db_session
from app.core.security import create_access_token, hash_password
from app.main import app
from app.modules.identity.models import PlayerProfile, Role, User
from app.modules.identity.seed import seed_identity_defaults
from app.modules.operators.models import Operator
from app.modules.wallet.models import Wallet

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
    """Provide an asynchronous database session for wallet integration tests."""
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
    """Create a tenant operator for wallet tests and clean up on teardown."""
    unique_slug = f"wallet-op-{uuid.uuid4().hex[:8]}"
    op = Operator(
        name=f"Wallet Test Operator {unique_slug}",
        slug=unique_slug,
        is_active=True,
    )
    db_session.add(op)
    await db_session.commit()
    await db_session.refresh(op)

    yield op

    await db_session.delete(op)
    await db_session.commit()


@pytest_asyncio.fixture
async def test_user(
    db_session: AsyncSession, test_operator: Operator
) -> AsyncGenerator[User, None]:
    """Create a player user associated with test_operator."""
    from sqlalchemy import select

    stmt_role = select(Role).where(Role.name == "PLAYER")
    player_role = await db_session.scalar(stmt_role)

    user = User(
        operator_id=test_operator.id,
        email=f"player-{uuid.uuid4().hex[:8]}@casino.com",
        hashed_password=hash_password("SecurePassword123!"),
        is_active=True,
        is_verified=True,
    )
    if player_role:
        user.roles.append(player_role)

    profile = PlayerProfile(
        user=user,
        username=f"user_{uuid.uuid4().hex[:8]}",
        first_name="John",
        last_name="Doe",
    )
    db_session.add(user)
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(user)

    yield user


@pytest_asyncio.fixture
def auth_headers(test_user: User) -> dict[str, str]:
    """Generate HTTP Authorization headers with a valid JWT access token for test_user."""
    token = create_access_token(
        data={"sub": str(test_user.id)},
        expires_delta=timedelta(minutes=30),
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def test_wallet(
    db_session: AsyncSession, test_user: User, test_operator: Operator
) -> AsyncGenerator[Wallet, None]:
    """Create an initial empty wallet for test_user."""
    wallet = Wallet(
        user_id=test_user.id,
        operator_id=test_operator.id,
        balance=0,
        currency="CREDITS",
        is_locked=False,
    )
    db_session.add(wallet)
    await db_session.commit()
    await db_session.refresh(wallet)

    yield wallet
