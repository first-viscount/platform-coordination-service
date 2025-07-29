"""Example endpoints demonstrating structured logging patterns."""

from typing import Dict, Any
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


class BusinessEvent(BaseModel):
    """Example business event model."""

    event_type: str
    user_id: str
    metadata: Dict[str, Any]


class EventResponse(BaseModel):
    """Response for business events."""

    event_id: str
    timestamp: datetime
    status: str


@router.post(
    "/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED
)
async def create_business_event(event: BusinessEvent) -> EventResponse:
    """Example endpoint for creating business events with structured logging."""
    import uuid

    event_id = str(uuid.uuid4())

    # Log the business event with structured data
    logger.info(
        "business_event_received",
        event_id=event_id,
        event_type=event.event_type,
        user_id=event.user_id,
        metadata=event.metadata,
    )

    try:
        # Simulate some business logic
        if event.event_type == "error":
            raise ValueError("Simulated error for demonstration")

        # Log successful processing
        logger.info(
            "business_event_processed",
            event_id=event_id,
            event_type=event.event_type,
            user_id=event.user_id,
            processing_time_ms=100,  # Simulated
        )

        return EventResponse(
            event_id=event_id,
            timestamp=datetime.now(timezone.utc),
            status="processed",
        )

    except ValueError as e:
        # Log business logic errors
        logger.warning(
            "business_event_failed",
            event_id=event_id,
            event_type=event.event_type,
            user_id=event.user_id,
            error=str(e),
            error_type="validation_error",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except Exception as e:
        # Log unexpected errors
        logger.error(
            "business_event_error",
            event_id=event_id,
            event_type=event.event_type,
            user_id=event.user_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/events/{event_id}")
async def get_event(event_id: str) -> Dict[str, Any]:
    """Example endpoint showing logging with path parameters."""
    logger.info("event_lookup_requested", event_id=event_id)

    # Simulate event lookup
    if event_id == "not-found":
        logger.warning("event_not_found", event_id=event_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {event_id} not found",
        )

    result = {
        "event_id": event_id,
        "status": "found",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    logger.info("event_lookup_completed", event_id=event_id, found=True)

    return result
