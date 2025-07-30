"""Error response models for consistent API error handling."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class ErrorDetail(BaseModel):
    """Detailed error information."""

    field: str | None = Field(None, description="Field that caused the error")
    message: str = Field(..., description="Error message")
    code: str | None = Field(None, description="Application-specific error code")


class ErrorResponse(BaseModel):
    """Standard error response format."""

    model_config = ConfigDict()

    error: str = Field(..., description="General error type or title")
    message: str = Field(..., description="Human-readable error message")
    details: list[ErrorDetail] | None = Field(
        None, description="Detailed error information"
    )
    correlation_id: str | None = Field(
        None, description="Request correlation ID for tracing"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Error timestamp"
    )
    path: str | None = Field(None, description="Request path that caused the error")
    status_code: int = Field(..., description="HTTP status code")

    # Development-only fields
    debug_info: dict[str, Any] | None = Field(
        None, description="Debug information (dev only)"
    )
    traceback: list[str] | None = Field(None, description="Stack trace (dev only)")

    @field_serializer("timestamp")
    def serialize_timestamp(self, timestamp: datetime, _info: Any) -> str:
        """Serialize timestamp to ISO format string."""
        return timestamp.isoformat()


class ValidationErrorDetail(ErrorDetail):
    """Validation-specific error detail."""

    # field is inherited from ErrorDetail, but we document that it's expected to be non-None for validation errors
    value: Any | None = Field(None, description="The invalid value (sanitized)")
    constraint: str | None = Field(
        None, description="Validation constraint that failed"
    )
