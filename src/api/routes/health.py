"""Health check endpoints."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, field_serializer

from src.core.config import settings
from src.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    timestamp: datetime
    service: str
    version: str

    @field_serializer("timestamp")
    def serialize_timestamp(self, timestamp: datetime, _info: Any) -> str:
        """Serialize timestamp to ISO format string."""
        return timestamp.isoformat()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service Health Check",
    description="""
Check the health status of the Platform Coordination Service.

This endpoint provides basic health information including:
- Current service status
- Server timestamp
- Service name and version

Use this endpoint for:
- Container health checks
- Load balancer health probes
- Monitoring system checks
- Service discovery validation
    """,
    response_description="Health status information",
    responses={
        200: {
            "description": "Service is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "timestamp": "2025-01-29T12:00:00Z",
                        "service": "platform-coordination-service",
                        "version": "0.1.0",
                    }
                }
            },
        },
        503: {
            "description": "Service is unhealthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "unhealthy",
                        "timestamp": "2025-01-29T12:00:00Z",
                        "service": "platform-coordination-service",
                        "version": "0.1.0",
                    }
                }
            },
        },
    },
    tags=["health", "monitoring"],
)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    logger.debug("health_check_requested")

    response = HealthResponse(
        status="healthy",
        timestamp=datetime.now(UTC),
        service=settings.app_name,
        version=settings.app_version,
    )

    logger.info(
        "health_check_completed",
        status=response.status,
        service=response.service,
        version=response.version,
    )

    return response
