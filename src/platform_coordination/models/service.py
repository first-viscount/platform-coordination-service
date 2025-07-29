"""Service registration models."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ServiceStatus(str, Enum):
    """Service health status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ServiceType(str, Enum):
    """Types of services in the platform."""

    API = "api"
    WORKER = "worker"
    DATABASE = "database"
    CACHE = "cache"
    MESSAGE_BROKER = "message_broker"
    OTHER = "other"


class ServiceMetadata(BaseModel):
    """Additional service metadata."""

    version: str
    environment: str = "development"
    region: str | None = None
    tags: dict[str, str] = Field(default_factory=dict)
    capabilities: list[str] = Field(default_factory=list)


class ServiceRegistration(BaseModel):
    """Service registration request."""

    name: str = Field(..., min_length=1, max_length=100)
    type: ServiceType
    host: str
    port: int = Field(..., ge=1, le=65535)
    metadata: ServiceMetadata
    health_check_endpoint: str = "/health"

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure service name follows naming conventions."""
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                "Service name must contain only alphanumeric characters, hyphens, and underscores"
            )
        return v.lower()


class ServiceInfo(BaseModel):
    """Complete service information."""

    id: str
    name: str
    type: ServiceType
    host: str
    port: int
    status: ServiceStatus
    metadata: ServiceMetadata
    health_check_endpoint: str
    registered_at: datetime
    last_seen_at: datetime
    health_check_failures: int = 0

    @property
    def url(self) -> str:
        """Get the service URL."""
        return f"http://{self.host}:{self.port}"

    @property
    def health_url(self) -> str:
        """Get the health check URL."""
        return f"{self.url}{self.health_check_endpoint}"


class ServiceHealth(BaseModel):
    """Service health check response."""

    service_id: str
    status: ServiceStatus
    checked_at: datetime
    response_time_ms: float | None = None
    error: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
