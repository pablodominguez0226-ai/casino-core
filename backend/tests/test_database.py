import inspect
import uuid

import pytest
from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.database import (
    AsyncSessionLocal,
    Base,
    TimestampMixin,
    engine,
    get_db_session,
    utc_now,
)
from app.modules.operators.models import Operator


def test_database_engine_configuration() -> None:
    """Validate that the SQLAlchemy engine is configured with correct pool and async driver."""
    assert isinstance(engine, AsyncEngine)

    # Validate pool configuration
    pool = engine.pool
    assert pool.size() == 10
    assert pool._pre_ping is True

    # Validate driver and URL
    url = engine.url
    assert url.drivername == "postgresql+asyncpg"
    assert url.database == settings.POSTGRES_DB
    assert url.username == settings.POSTGRES_USER
    assert url.host == settings.POSTGRES_SERVER
    assert url.port == settings.POSTGRES_PORT


def test_async_session_maker_configuration() -> None:
    """Validate the async_sessionmaker setup and settings."""
    assert isinstance(AsyncSessionLocal, async_sessionmaker)
    assert AsyncSessionLocal.kw.get("expire_on_commit") is False
    assert AsyncSessionLocal.kw.get("autoflush") is False
    assert AsyncSessionLocal.class_ is AsyncSession


def test_get_db_session_is_async_generator() -> None:
    """Validate that get_db_session is an async generator function for FastAPI dependency."""
    assert inspect.isasyncgenfunction(get_db_session)


def test_operator_model_metadata() -> None:
    """Validate Operator entity columns, types, nullability, and constraints."""
    table = Operator.__table__

    assert table.name == "operators"
    assert issubclass(Operator, Base)
    assert issubclass(Operator, TimestampMixin)

    # Check primary key
    id_col = table.c.id
    assert id_col.primary_key is True
    assert id_col.nullable is False

    # Check name column
    name_col = table.c.name
    assert isinstance(name_col.type, String)
    assert name_col.type.length == 100
    assert name_col.nullable is False

    # Check slug column
    slug_col = table.c.slug
    assert isinstance(slug_col.type, String)
    assert slug_col.type.length == 50
    assert slug_col.nullable is False
    assert slug_col.unique is True
    assert slug_col.index is True

    # Check is_active column
    is_active_col = table.c.is_active
    assert isinstance(is_active_col.type, Boolean)
    assert is_active_col.nullable is False
    assert is_active_col.default.arg is True

    # Check timestamp mixin columns
    created_at_col = table.c.created_at
    assert isinstance(created_at_col.type, DateTime)
    assert created_at_col.type.timezone is True
    assert created_at_col.nullable is False

    updated_at_col = table.c.updated_at
    assert isinstance(updated_at_col.type, DateTime)
    assert updated_at_col.type.timezone is True
    assert updated_at_col.nullable is False


def test_operator_instance_creation() -> None:
    """Validate creating an Operator entity instance with default and custom values."""
    op_id = uuid.uuid4()
    operator = Operator(
        id=op_id,
        name="Alpha Casino",
        slug="alpha-casino",
        is_active=True,
    )

    assert operator.id == op_id
    assert operator.name == "Alpha Casino"
    assert operator.slug == "alpha-casino"
    assert operator.is_active is True
    assert "Alpha Casino" not in repr(operator)
    assert "alpha-casino" in repr(operator)


def test_utc_now_returns_timezone_aware_datetime() -> None:
    """Validate that utc_now helper returns a UTC timezone-aware datetime."""
    now = utc_now()
    assert now.tzinfo is not None
    assert str(now.tzinfo) == "UTC"


def test_core_exceptions() -> None:
    """Validate core and domain exceptions hierarchy and attributes."""
    from app.core.exceptions import (
        AppException,
        DatabaseConnectionError,
        EntityAlreadyExistsError,
        EntityNotFoundError,
    )

    base_exc = AppException("Custom error", status_code=400, details={"info": "test"})
    assert base_exc.message == "Custom error"
    assert base_exc.status_code == 400
    assert base_exc.details == {"info": "test"}

    db_exc = DatabaseConnectionError("DB Down")
    assert db_exc.status_code == 503
    assert db_exc.message == "DB Down"

    not_found_exc = EntityNotFoundError(entity_name="Operator", identifier="test-uuid")
    assert not_found_exc.status_code == 404
    assert "Operator with identifier 'test-uuid' was not found" in str(not_found_exc)
    assert not_found_exc.details["entity_name"] == "Operator"

    duplicate_exc = EntityAlreadyExistsError(
        entity_name="Operator", conflict_field="slug", value="alpha-casino"
    )
    assert duplicate_exc.status_code == 409
    assert "Operator with slug 'alpha-casino' already exists" in str(duplicate_exc)


@pytest.mark.asyncio
async def test_get_db_session_context_management() -> None:
    """Validate get_db_session yields a session and handles rollback on error."""
    from unittest.mock import AsyncMock, patch

    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None

    with patch("app.core.database.AsyncSessionLocal", return_value=mock_session):
        # Successful execution
        gen = get_db_session()
        yielded_session = await anext(gen)
        assert yielded_session is mock_session
        await gen.aclose()

    # Exception during yield triggers rollback
    mock_failing_session = AsyncMock(spec=AsyncSession)
    mock_failing_session.__aenter__.return_value = mock_failing_session
    mock_failing_session.__aexit__.return_value = None

    with patch("app.core.database.AsyncSessionLocal", return_value=mock_failing_session):
        gen = get_db_session()
        await anext(gen)
        with pytest.raises(RuntimeError, match="Simulated query error"):
            await gen.athrow(RuntimeError("Simulated query error"))

        mock_failing_session.rollback.assert_awaited_once()
        mock_failing_session.close.assert_awaited_once()



