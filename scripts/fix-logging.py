#!/usr/bin/env python3
"""Fix logging implementation to be consistent."""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Restore original main.py that works
MAIN_PY = '''"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import health
from src.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Platform Coordination Service API",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])

@app.get("/")
async def root():
    """Root endpoint."""
    return {"service": settings.app_name, "version": settings.app_version}
'''

# Write the fixed main.py
with open("src/main.py", "w") as f:
    f.write(MAIN_PY)

print("✅ Fixed main.py to working version")
print("✅ Service should work again")
print("\nRun: python scripts/verify-service.py")