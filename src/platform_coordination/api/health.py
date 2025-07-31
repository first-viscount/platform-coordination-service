"""Health check endpoints."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter

from src.platform_coordination.core.config import settings

router = APIRouter()


@router.get("/")
async def health_check() -> dict[str, Any]:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/ready")
async def readiness_check() -> dict[str, Any]:
    """Readiness check endpoint."""
    # TODO: Add checks for database connectivity, etc.
    return {
        "ready": True,
        "checks": {
            "database": "ok",  # Placeholder
        },
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/live")
async def liveness_check() -> dict[str, str]:
    """Liveness check endpoint."""
    return {
        "status": "alive",
        "timestamp": datetime.now(UTC).isoformat(),
    }
