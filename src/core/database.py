"""Database configuration and session management."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)

# Create async engine
engine = create_async_engine(
    settings.database_url
    or "postgresql+asyncpg://coordination_user:coordination_dev_password@localhost:5432/platform_coordination",
    echo=settings.environment == "development",
    pool_size=getattr(settings, "db_pool_size", 10),
    max_overflow=getattr(settings, "db_pool_max_overflow", 20),
    pool_timeout=getattr(settings, "db_pool_timeout", 30),
    pool_pre_ping=True,
)

# Create async session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for SQLAlchemy models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    async with async_session() as session:
        try:
            # Update pool metrics if available
            _update_pool_metrics()
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def _update_pool_metrics() -> None:
    """Update database connection pool metrics."""
    try:
        # Import here to avoid circular imports
        from src.core.metrics import get_metrics_collector
        
        metrics = get_metrics_collector()
        
        # Get pool statistics if available
        if hasattr(engine, "pool"):
            pool = engine.pool
            metrics.update_db_pool_metrics(
                pool_size=pool.size(),
                checked_out=pool.checkedout(),
                overflow=pool.overflow(),
            )
    except Exception as e:
        logger.debug("Could not update pool metrics", error=str(e))


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager to get database session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database (create tables if needed)."""
    try:
        async with engine.begin() as conn:
            # In production, use Alembic migrations instead
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()
    logger.info("Database connections closed")
