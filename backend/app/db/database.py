"""
Database engine and session factory.

Supports two backends via DATABASE_URL in .env:

  SQLite (local dev, no Docker required):
    DATABASE_URL=sqlite+aiosqlite:///./brandshield.db

  PostgreSQL (when available / production):
    DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/brandshield

The application code is identical for both — only the URL changes.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator

from app.core.config import settings


def _build_engine_kwargs() -> dict:
    """
    SQLite does not support connection pool settings (pool_size, max_overflow).
    PostgreSQL does. Build kwargs dynamically based on the URL scheme.
    """
    url = settings.database_url
    if url.startswith("sqlite"):
        # SQLite: single-file async, no pool needed
        return {
            "echo": settings.app_debug,
            # Required for SQLite to work correctly with async
            "connect_args": {"check_same_thread": False},
        }
    else:
        # PostgreSQL / other async-capable databases
        return {
            "echo": settings.app_debug,
            "pool_pre_ping": True,
            "pool_size": 5,
            "max_overflow": 10,
        }


engine = create_async_engine(settings.database_url, **_build_engine_kwargs())

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency — yields a database session per request.
    Commits on success, rolls back on error, always closes.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_all_tables() -> None:
    """
    Create all tables defined by ORM models.
    Called at application startup (development / SQLite only).
    For PostgreSQL in production, use Alembic migrations instead.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
