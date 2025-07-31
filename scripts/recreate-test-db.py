#!/usr/bin/env python3
"""Recreate test database schema."""

import asyncio
import os
import sys
sys.path.insert(0, 'src')

from sqlalchemy.ext.asyncio import create_async_engine
from src.core.database import Base

async def recreate_schema():
    """Drop and recreate all tables."""
    test_db_url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://coordination_user:coordination_dev_password@localhost:5432/platform_coordination_test"
    )
    
    print(f"Recreating schema for: {test_db_url}")
    
    engine = create_async_engine(test_db_url, echo=True)
    
    async with engine.begin() as conn:
        print("Dropping all tables...")
        await conn.run_sync(Base.metadata.drop_all)
        print("Creating all tables...")
        await conn.run_sync(Base.metadata.create_all)
        
    await engine.dispose()
    print("Schema recreated successfully!")

if __name__ == "__main__":
    asyncio.run(recreate_schema())