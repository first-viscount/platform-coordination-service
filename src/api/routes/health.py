"""Health check endpoints."""

from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel

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


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    logger.debug("health_check_requested")

    response = HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
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
