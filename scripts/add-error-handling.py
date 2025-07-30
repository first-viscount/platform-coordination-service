#!/usr/bin/env python3
"""Add error handling middleware to the application."""

import os

# Updated main.py with error handling middleware
MAIN_PY = '''"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import health, example
from src.api.middleware.error_handling import ErrorHandlingMiddleware
from src.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Platform Coordination Service API",
)

# Add error handling middleware (must be first)
app.add_middleware(ErrorHandlingMiddleware)

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
app.include_router(example.router, prefix="/api/v1", tags=["examples"])

@app.get("/")
async def root():
    """Root endpoint."""
    return {"service": settings.app_name, "version": settings.app_version}
'''

# Write the updated main.py
with open("src/main.py", "w") as f:
    f.write(MAIN_PY)

print("✅ Added error handling middleware to main.py")
print("✅ Included example routes to test error handling")
print("\nTo test error handling:")
print("1. Run: make verify")
print("2. Or start the service and try:")
print("   - GET /api/v1/examples/not-found")
print("   - GET /api/v1/examples/validation-error")
print("   - GET /api/v1/examples/internal-error")