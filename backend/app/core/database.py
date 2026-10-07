from collections.abc import AsyncGenerator
from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import settings


def utc_now() -> datetime:
    """Return the current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class Base(AsyncAttrs, DeclarativeBase):
    """Base declarative class for all SQLAlchemy ORM models in CasinoCore."""

    pass


class TimestampMixin:
    """Reusable model mixin adding timezone-aware created_at and updated_at fields."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


# Asynchronous SQLAlchemy Engine
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.POSTGRES_ECHO,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Asynchronous session factory
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
