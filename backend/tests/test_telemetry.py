from collections.abc import AsyncGenerator
from datetime import datetime
import json
import logging
import uuid

import httpx
from httpx import ASGITransport
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import get_db_session
from app.core.security import create_access_token, hash_password
from app.core.telemetry.logging import JSONFormatter, request_id_ctx, setup_telemetry_logging
from app.core.telemetry.metrics import MetricsCollector, metrics_collector
from app.main import app
from app.modules.identity.models import PlayerProfile, Role, User
from app.modules.identity.seed import seed_identity_defaults
from app.modules.operators.models import Operator
from app.modules.wallet.enums import LedgerEntryType
from app.modules.wallet.models import Wallet
from app.modules.wallet.services import WalletService

# NullPool test engine
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
    """Provide an asynchronous database session with seeded identity permissions."""
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
    """Provide a seeded Operator entity for telemetry integration tests."""
    stmt = select(Operator).where(Operator.slug == "telemetry-test-operator")
    operator = await db_session.scalar(stmt)
    if not operator:
        operator = Operator(
            name="Telemetry Test Operator",
            slug="telemetry-test-operator",
            is_active=True,
        )
        db_session.add(operator)
        await db_session.commit()
        await db_session.refresh(operator)
    yield operator


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession, test_operator: Operator) -> AsyncGenerator[User, None]:
    """Provide a test User entity."""
    user = User(
        operator_id=test_operator.id,
        email=f"telemetry_user_{uuid.uuid4()}@casino.com",
        hashed_password=hash_password("UserPassword123!"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    profile = PlayerProfile(user_id=user.id, username=f"telemetry_{uuid.uuid4().hex[:6]}")
    db_session.add(profile)
    await db_session.commit()

    yield user


def test_json_formatter_standard_fields() -> None:
    """Validate JSONFormatter serializes log records into valid JSON with mandatory fields."""
    formatter = JSONFormatter()
    logger = logging.getLogger("test.logger")
    record = logger.makeRecord(
        name="test.logger",
        level=logging.INFO,
        fn="test_file.py",
        lno=42,
        msg="Test message format %s",
        args=("successfully",),
        exc_info=None,
    )

    formatted = formatter.format(record)
    parsed = json.loads(formatted)

    assert parsed["level"] == "INFO"
    assert parsed["message"] == "Test message format successfully"
    assert parsed["module"] == "test.logger"
    assert parsed["request_id"] is None
    assert parsed["exception"] is None
    datetime.fromisoformat(parsed["timestamp"])


def test_json_formatter_with_contextvar_and_exception() -> None:
    """Validate JSONFormatter extracts request_id from ContextVar and formats exceptions."""
    formatter = JSONFormatter()
    logger = logging.getLogger("test.logger.exc")

    test_req_id = f"trace-{uuid.uuid4()}"
    token = request_id_ctx.set(test_req_id)

    try:
        try:
            raise ValueError("Deliberate testing exception")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = logger.makeRecord(
            name="test.logger.exc",
            level=logging.ERROR,
            fn="test_file.py",
            lno=100,
            msg="An error occurred",
            args=(),
            exc_info=exc_info,
        )
        record.client_ip = "192.168.1.50"
        record.latency_ms = 14.2

        formatted = formatter.format(record)
        parsed = json.loads(formatted)

        assert parsed["level"] == "ERROR"
        assert parsed["message"] == "An error occurred"
        assert parsed["request_id"] == test_req_id
        assert "ValueError: Deliberate testing exception" in parsed["exception"]
        assert parsed["client_ip"] == "192.168.1.50"
        assert parsed["latency_ms"] == 14.2
    finally:
        request_id_ctx.reset(token)


def test_setup_telemetry_logging() -> None:
    """Validate setup_telemetry_logging attaches StreamHandler with JSONFormatter to root logger."""
    setup_telemetry_logging("DEBUG")
    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG
    assert len(root_logger.handlers) >= 1
    assert any(isinstance(h.formatter, JSONFormatter) for h in root_logger.handlers)


def test_metrics_collector_operations() -> None:
    """Validate MetricsCollector correctly records requests, latency, and financial transactions."""
    collector = MetricsCollector()
    collector.reset()

    # Initial state
    metrics = collector.get_metrics()
    assert metrics["total_requests"] == 0
    assert metrics["average_latency_ms"] == 0.0
    assert metrics["total_financial_transactions"] == 0

    # Record some requests
    collector.record_request(200, 10.0)
    collector.record_request(200, 20.0)
    collector.record_request(404, 30.0)
    collector.record_request(500, 40.0)

    # Record financial transactions
    collector.record_financial_transaction(1)
    collector.record_financial_transaction(2)

    updated = collector.get_metrics()
    assert updated["total_requests"] == 4
    assert updated["average_latency_ms"] == 25.0
    assert updated["requests_by_status"]["2xx"] == 2
    assert updated["requests_by_status"]["4xx"] == 1
    assert updated["requests_by_status"]["5xx"] == 1
    assert updated["requests_by_status_code"]["200"] == 2
    assert updated["requests_by_status_code"]["404"] == 1
    assert updated["requests_by_status_code"]["500"] == 1
    assert updated["total_financial_transactions"] == 3


@pytest.mark.asyncio
async def test_telemetry_middleware_generates_request_id(client: httpx.AsyncClient) -> None:
    """Validate TelemetryMiddleware automatically generates UUIDv4 X-Request-ID when not provided."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    uuid.UUID(response.headers["X-Request-ID"])


@pytest.mark.asyncio
async def test_telemetry_middleware_propagates_request_id(client: httpx.AsyncClient) -> None:
    """Validate TelemetryMiddleware propagates incoming client X-Request-ID header."""
    custom_id = f"custom-req-id-{uuid.uuid4()}"
    response = await client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_id


@pytest.mark.asyncio
async def test_metrics_endpoint_unauthenticated_forbidden(client: httpx.AsyncClient) -> None:
    """Validate GET /api/v1/metrics rejects unauthenticated requests with 401 Unauthorized."""
    response = await client.get("/api/v1/metrics")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_metrics_endpoint_player_forbidden(
    client: httpx.AsyncClient, db_session: AsyncSession, test_operator: Operator
) -> None:
    """Validate GET /api/v1/metrics rejects players with 403 Forbidden."""
    role_stmt = select(Role).where(Role.name == "PLAYER").options(selectinload(Role.permissions))
    player_role = await db_session.scalar(role_stmt)

    player = User(
        operator_id=test_operator.id,
        email=f"player_metrics_{uuid.uuid4()}@casino.com",
        hashed_password=hash_password("PlayerPass123!"),
        is_active=True,
        roles=[player_role] if player_role else [],
    )
    db_session.add(player)
    await db_session.commit()
    await db_session.refresh(player)

    token = create_access_token(data={"sub": str(player.id), "operator_id": str(test_operator.id)})
    response = await client.get(
        "/api/v1/metrics",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert "Admin or monitor privilege required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_metrics_endpoint_admin_authorized(
    client: httpx.AsyncClient, db_session: AsyncSession, test_operator: Operator
) -> None:
    """Validate GET /api/v1/metrics allows SUPER_ADMIN and returns accurate telemetry payload."""
    role_stmt = select(Role).where(Role.name == "SUPER_ADMIN").options(selectinload(Role.permissions))
    admin_role = await db_session.scalar(role_stmt)

    admin = User(
        operator_id=test_operator.id,
        email=f"admin_metrics_{uuid.uuid4()}@casino.com",
        hashed_password=hash_password("AdminPass123!"),
        is_active=True,
        roles=[admin_role] if admin_role else [],
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)

    token = create_access_token(data={"sub": str(admin.id), "operator_id": str(test_operator.id)})
    response = await client.get(
        "/api/v1/metrics",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_requests" in data
    assert "requests_by_status" in data
    assert "requests_by_status_code" in data
    assert "average_latency_ms" in data
    assert "total_financial_transactions" in data
    assert "uptime_seconds" in data
    assert data["total_requests"] >= 1


@pytest.mark.asyncio
async def test_financial_transactions_counter_increments_on_wallet_operations(
    db_session: AsyncSession, test_user: User, test_operator: Operator
) -> None:
    """Validate WalletService execution updates metrics_collector financial transactions counter."""
    initial_financial_txs = metrics_collector.get_metrics()["total_financial_transactions"]

    wallet = Wallet(
        user_id=test_user.id,
        operator_id=test_operator.id,
        balance=500,
        currency="CREDITS",
    )
    db_session.add(wallet)
    await db_session.commit()
    await db_session.refresh(wallet)

    # Perform a credit operation
    await WalletService.execute_transaction(
        db=db_session,
        wallet_id=wallet.id,
        amount=100,
        entry_type=LedgerEntryType.CREDIT,
        idempotency_key=f"met-credit-{uuid.uuid4()}",
    )

    current_financial_txs = metrics_collector.get_metrics()["total_financial_transactions"]
    assert current_financial_txs == initial_financial_txs + 1
