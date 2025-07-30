"""Service registry API endpoints."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from structlog import get_logger

from platform_coordination.models.service import (
    ServiceInfo,
    ServiceRegistration,
    ServiceStatus,
    ServiceType,
)

router = APIRouter()
logger = get_logger(__name__)

# In-memory storage for now (will be replaced with database)
service_registry: dict[str, ServiceInfo] = {}


@router.post("/register", response_model=ServiceInfo, status_code=201)
async def register_service(registration: ServiceRegistration) -> ServiceInfo:
    """Register a new service or update existing registration."""
    # Check if service already exists
    existing_service = None
    for _service_id, service in service_registry.items():
        if (
            service.name == registration.name
            and service.host == registration.host
            and service.port == registration.port
        ):
            existing_service = service
            break

    if existing_service:
        # Update existing service
        service_id = existing_service.id
        logger.info(
            "Updating existing service registration",
            service_id=service_id,
            service_name=registration.name,
        )
    else:
        # Create new service
        service_id = str(uuid4())
        logger.info(
            "Registering new service",
            service_id=service_id,
            service_name=registration.name,
        )

    now = datetime.now(UTC)
    service_info = ServiceInfo(
        id=service_id,
        name=registration.name,
        type=registration.type,
        host=registration.host,
        port=registration.port,
        status=ServiceStatus.UNKNOWN,  # Will be updated by health checks
        metadata=registration.metadata,
        health_check_endpoint=registration.health_check_endpoint,
        registered_at=existing_service.registered_at if existing_service else now,
        last_seen_at=now,
        health_check_failures=0,
    )

    service_registry[service_id] = service_info
    return service_info


@router.get("/", response_model=list[ServiceInfo])
async def list_services(
    type: Annotated[
        ServiceType | None, Query(description="Filter by service type")
    ] = None,
    status: Annotated[
        ServiceStatus | None, Query(description="Filter by service status")
    ] = None,
    tag: Annotated[
        str | None, Query(description="Filter by tag (format: key=value)")
    ] = None,
) -> list[ServiceInfo]:
    """List all registered services with optional filters."""
    services = list(service_registry.values())

    # Apply filters
    if type:
        services = [s for s in services if s.type == type]

    if status:
        services = [s for s in services if s.status == status]

    if tag:
        try:
            key, value = tag.split("=", 1)
            services = [s for s in services if s.metadata.tags.get(key) == value]
        except ValueError:
            raise HTTPException(400, "Invalid tag format. Use key=value") from None

    logger.info(
        "Listed services",
        count=len(services),
        filters={"type": type, "status": status, "tag": tag},
    )

    return services


@router.get("/{service_id}", response_model=ServiceInfo)
async def get_service(service_id: str) -> ServiceInfo:
    """Get detailed information about a specific service."""
    service = service_registry.get(service_id)
    if not service:
        logger.warning("Service not found", service_id=service_id)
        raise HTTPException(404, f"Service {service_id} not found")

    return service


@router.delete("/{service_id}", status_code=204)
async def unregister_service(service_id: str) -> None:
    """Unregister a service."""
    service = service_registry.pop(service_id, None)
    if not service:
        logger.warning(
            "Attempted to unregister non-existent service", service_id=service_id
        )
        raise HTTPException(404, f"Service {service_id} not found")

    logger.info(
        "Service unregistered", service_id=service_id, service_name=service.name
    )


@router.get("/discover/{service_name}", response_model=list[ServiceInfo])
async def discover_services(
    service_name: str,
    status: Annotated[
        ServiceStatus, Query(description="Minimum acceptable status")
    ] = ServiceStatus.HEALTHY,
) -> list[ServiceInfo]:
    """Discover services by name, returning only healthy instances."""
    services = [
        s
        for s in service_registry.values()
        if s.name == service_name.lower() and s.status == status
    ]

    if not services:
        logger.info(
            "No healthy services found",
            service_name=service_name,
            required_status=status,
        )

    return services
