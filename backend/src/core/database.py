"""Database session management and configuration."""

import logging
import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..models.base import Base
from .config import config

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/trading_agent"
)

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

logger.info(
    f"Database pool configured: pool_size={config.DB_POOL_SIZE}, "
    f"max_overflow={config.DB_MAX_OVERFLOW}, recycle={config.DB_POOL_RECYCLE}s"
)

# For async engines, SQLAlchemy 2.0 uses asyncpg's built-in connection pooling
# We pass pool_size and max_overflow as connect_args for asyncpg
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=config.DB_POOL_SIZE,
    max_overflow=config.DB_MAX_OVERFLOW,
    pool_recycle=config.DB_POOL_RECYCLE,
    pool_pre_ping=config.DB_POOL_PRE_PING,
    connect_args={
        # asyncpg-specific connection settings
        "timeout": 10,  # Connection timeout
        "command_timeout": 5,  # Command timeout
        "server_settings": {
            "application_name": "0xBot",
            "jit": "off",  # Disable JIT for better performance on simple queries
        },
    },
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI endpoints to get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables. In production, use Alembic migrations."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()
