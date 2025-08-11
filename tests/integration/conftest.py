"""Pytest configuration for integration tests."""

import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from src.core.database import Base, get_db
from src.main_db import app

# Test database URL - use separate test database
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://coordination_user:coordination_dev_password@localhost:5432/platform_coordination_test"
)


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create a test database engine."""
    # Use NullPool to avoid connection pool issues in tests
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def setup_database(test_engine):
    """Create all tables before each test and drop them after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine, setup_database) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def test_client(test_engine, setup_database):
    """Create a test client with proper database session handling."""
    from sqlalchemy.ext.asyncio import async_sessionmaker
    
    # Create a session factory for the test
    TestSessionLocal = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async def override_get_db():
        async with TestSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    import httpx
    
    async with httpx.AsyncClient(base_url="http://test", transport=httpx.ASGITransport(app=app)) as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_service_data():
    """Sample service registration data."""
    return {
        "name": "test-api",
        "type": "api",
        "host": "localhost",
        "port": 8080,
        "metadata": {
            "version": "1.0.0",
            "environment": "test",
            "tags": {
                "team": "platform"
            }
        },
        "health_check_endpoint": "/health"
    }


@pytest.fixture
def multiple_services_data():
    """Multiple service registrations for testing."""
    return [
        {
            "name": "api-service",
            "type": "api",
            "host": "api.example.com",
            "port": 8080,
            "metadata": {"version": "1.0.0", "environment": "production", "tags": {"env": "prod", "region": "us-east"}}
        },
        {
            "name": "worker-service",
            "type": "worker",
            "host": "worker1.example.com",
            "port": 9090,
            "metadata": {"version": "1.0.0", "environment": "production", "tags": {"env": "prod", "region": "us-west"}}
        },
        {
            "name": "scheduler-service",
            "type": "worker", 
            "host": "scheduler.example.com",
            "port": 7070,
            "metadata": {"version": "1.0.0", "environment": "staging", "tags": {"env": "staging", "region": "us-east"}}
        },
        {
            "name": "cache-service",
            "type": "cache",
            "host": "cache.example.com",
            "port": 6379,
            "metadata": {"version": "1.0.0", "environment": "production", "tags": {"env": "prod", "region": "us-east"}}
        }
    ]