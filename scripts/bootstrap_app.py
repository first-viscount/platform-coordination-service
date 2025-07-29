#!/usr/bin/env python3
"""Bootstrap script to create minimal FastAPI application structure."""

import os
import sys
from pathlib import Path

# Define the minimal FastAPI application files
FILES = {
    "src/__init__.py": '"""Platform Coordination Service."""\n\n__version__ = "0.1.0"',
    
    "src/main.py": '''"""Main FastAPI application."""

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
''',

    "src/core/__init__.py": '"""Core functionality."""',
    
    "src/core/config.py": '''"""Application configuration."""

from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    app_name: str = "platform-coordination-service"
    app_version: str = "0.1.0"
    
    # CORS
    cors_origins: List[str] = ["http://localhost:3000"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
''',

    "src/api/__init__.py": '"""API routes and dependencies."""',
    
    "src/api/routes/__init__.py": '"""API route modules."""',
    
    "src/api/routes/health.py": '''"""Health check endpoints."""

from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel

from src.core.config import settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime
    service: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        service=settings.app_name,
        version=settings.app_version,
    )
''',

    "tests/__init__.py": '"""Tests for Platform Coordination Service."""',
    
    "tests/test_health.py": '''"""Test health endpoints."""

from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "platform-coordination-service"


def test_root():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "version" in data
''',
}


def create_structure():
    """Create the application structure."""
    base_dir = Path(__file__).parent.parent
    
    created_files = []
    for file_path, content in FILES.items():
        full_path = base_dir / file_path
        
        # Create directory if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        full_path.write_text(content)
        created_files.append(file_path)
        print(f"✓ Created {file_path}")
    
    print(f"\n✅ Created {len(created_files)} files")
    print("\nNext steps:")
    print("1. Install dependencies: make install-dev")
    print("2. Run the service: make run")
    print("3. Run tests: make test")
    print("4. Check health: curl http://localhost:8000/health")


if __name__ == "__main__":
    create_structure()