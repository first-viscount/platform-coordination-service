"""SQLAlchemy models for service registry."""

import enum
from datetime import UTC, datetime
from uuid import UUID as UUID_TYPE
from uuid import uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class ServiceStatus(str, enum.Enum):
    """Service status enumeration."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    STARTING = "starting"
    STOPPING = "stopping"
    STOPPED = "stopped"


class ServiceType(str, enum.Enum):
    """Service type enumeration."""

    API = "api"
    WORKER = "worker"
    SCHEDULER = "scheduler"
    GATEWAY = "gateway"
    CACHE = "cache"
    DATABASE = "database"
    MESSAGE_BROKER = "message_broker"
    MONITORING = "monitoring"


class Service(Base):
    """Service model for the registry."""

    __tablename__ = "services"

    # Primary identification
    id: Mapped[UUID_TYPE] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[ServiceType] = mapped_column(Enum(ServiceType), nullable=False)

    # Network information
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        info={"check_constraints": [CheckConstraint("port > 0 AND port < 65536")]},
    )

    # Status and health
    status: Mapped[ServiceStatus] = mapped_column(
        Enum(ServiceStatus), nullable=False, default=ServiceStatus.UNKNOWN
    )
    health_check_endpoint: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    health_check_interval: Mapped[int] = mapped_column(Integer, default=30)  # seconds
    health_check_timeout: Mapped[int] = mapped_column(Integer, default=10)  # seconds
    health_check_failures: Mapped[int] = mapped_column(Integer, default=0)
    last_health_check_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Metadata stored as JSON
    service_metadata: Mapped[dict] = mapped_column(JSON, default=dict)

    # Timestamps
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Version for optimistic locking
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relationships
    events: Mapped[list["ServiceEvent"]] = relationship(
        "ServiceEvent", back_populates="service", cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("name", "host", "port", name="unique_service_endpoint"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<Service {self.name}@{self.host}:{self.port} [{self.status}]>"


class ServiceEvent(Base):
    """Service event model for audit trail."""

    __tablename__ = "service_events"

    id: Mapped[UUID_TYPE] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    service_id: Mapped[UUID_TYPE] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    event_data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    # Relationships
    service: Mapped["Service"] = relationship("Service", back_populates="events")

    def __repr__(self) -> str:
        """String representation."""
        return f"<ServiceEvent {self.event_type} for {self.service_id}>"
