"""Service registry API endpoints with database backend."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from src.api.models.service import (
    ServiceInfo,
    ServiceMetadata,
    ServiceRegistration,
    ServiceStatus,
    ServiceType,
)
from src.core.database import get_db
from src.core.exceptions import ConflictError
from src.models.service import Service as ServiceModel
from src.models.service import ServiceStatus as DBServiceStatus
from src.models.service import ServiceType as DBServiceType
from src.repositories.service import ServiceRepository

router = APIRouter()
logger = get_logger(__name__)


def _convert_to_service_info(service: ServiceModel) -> ServiceInfo:
    """Convert database model to API model."""
    # Extract metadata or provide defaults
    metadata_dict = service.service_metadata or {}
    metadata = ServiceMetadata(
        version=metadata_dict.get("version", "unknown"),
        environment=metadata_dict.get("environment", "development"),
        region=metadata_dict.get("region"),
        tags=metadata_dict.get("tags", {}),
        capabilities=metadata_dict.get("capabilities", [])
    )
    
    return ServiceInfo(
        id=str(service.id),
        name=service.name,
        type=ServiceType(service.type.value),
        host=service.host,
        port=service.port,
        status=ServiceStatus(service.status.value),
        metadata=metadata,
        health_check_endpoint=service.health_check_endpoint,
        registered_at=service.registered_at,
        last_seen_at=service.last_seen_at,
        health_check_failures=service.health_check_failures,
    )


@router.post("/register", response_model=ServiceInfo, status_code=201)
async def register_service(
    registration: ServiceRegistration,
    db: AsyncSession = Depends(get_db),
) -> ServiceInfo:
    """Register a new service or update existing registration."""
    repo = ServiceRepository(db)

    # Check if service already exists
    existing = await repo.get_by_name_host_port(
        registration.name, registration.host, registration.port
    )

    if existing:
        # Update existing service
        logger.info(
            "Updating existing service registration",
            service_id=str(existing.id),
            service_name=registration.name,
        )

        updated = await repo.update(
            existing.id,
            type=DBServiceType(registration.type.value),
            service_metadata=(
                registration.metadata.model_dump() if registration.metadata else {}
            ),
            health_check_endpoint=registration.health_check_endpoint,
            status=DBServiceStatus.UNKNOWN,  # Reset status on re-registration
        )

        if not updated:
            raise HTTPException(500, "Failed to update service")

        return _convert_to_service_info(updated)

    # Create new service
    try:
        service = await repo.create(
            name=registration.name,
            type=DBServiceType(registration.type.value),
            host=registration.host,
            port=registration.port,
            status=DBServiceStatus.UNKNOWN,
            service_metadata=(
                registration.metadata.model_dump() if registration.metadata else {}
            ),
            health_check_endpoint=registration.health_check_endpoint,
        )

        return _convert_to_service_info(service)
    except ConflictError:
        # This is a race condition - another request created it first
        # Try to get and update it instead
        existing = await repo.get_by_name_host_port(
            registration.name, registration.host, registration.port
        )
        if existing:
            logger.info(
                "Race condition detected, updating instead",
                service_id=str(existing.id),
                service_name=registration.name,
            )
            updated = await repo.update(
                existing.id,
                type=DBServiceType(registration.type.value),
                service_metadata=(
                    registration.metadata.model_dump() if registration.metadata else {}
                ),
                health_check_endpoint=registration.health_check_endpoint,
                status=DBServiceStatus.UNKNOWN,
            )
            if updated:
                return _convert_to_service_info(updated)
        
        # If we still can't handle it, raise the error
        raise HTTPException(409, "Service registration conflict") from None


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
    db: AsyncSession = Depends(get_db),
) -> list[ServiceInfo]:
    """List all registered services with optional filters."""
    repo = ServiceRepository(db)

    # Parse tag filter
    tag_key = tag_value = None
    if tag:
        try:
            tag_key, tag_value = tag.split("=", 1)
        except ValueError:
            raise HTTPException(400, "Invalid tag format. Use key=value") from None

    # Query services
    services = await repo.list(
        type=DBServiceType(type.value) if type else None,
        status=DBServiceStatus(status.value) if status else None,
        tag_key=tag_key,
        tag_value=tag_value,
    )

    logger.info(
        "Listed services",
        count=len(services),
        filters={"type": type, "status": status, "tag": tag},
    )

    return [_convert_to_service_info(s) for s in services]


@router.get("/{service_id}", response_model=ServiceInfo)
async def get_service(
    service_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ServiceInfo:
    """Get detailed information about a specific service."""
    repo = ServiceRepository(db)

    service = await repo.get(service_id)
    if not service:
        logger.warning("Service not found", service_id=str(service_id))
        raise HTTPException(404, f"Service {service_id} not found")

    return _convert_to_service_info(service)


@router.delete("/{service_id}", status_code=204)
async def unregister_service(
    service_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Unregister a service."""
    repo = ServiceRepository(db)

    # First check if service exists
    service = await repo.get(service_id)
    if not service:
        logger.warning(
            "Attempted to unregister non-existent service", service_id=str(service_id)
        )
        raise HTTPException(404, f"Service {service_id} not found")

    # Delete the service
    deleted = await repo.delete(service_id)
    if not deleted:
        raise HTTPException(500, "Failed to delete service")


@router.get("/discover/{service_name}", response_model=list[ServiceInfo])
async def discover_services(
    service_name: str,
    status: Annotated[
        ServiceStatus, Query(description="Minimum acceptable status")
    ] = ServiceStatus.HEALTHY,
    db: AsyncSession = Depends(get_db),
) -> list[ServiceInfo]:
    """Discover services by name, returning only healthy instances."""
    repo = ServiceRepository(db)

    services = await repo.find_by_name(
        service_name,
        DBServiceStatus(status.value),
    )

    if not services:
        logger.info(
            "No healthy services found",
            service_name=service_name,
            required_status=status,
        )
        return []

    return [_convert_to_service_info(s) for s in services]


@router.post("/{service_id}/health", response_model=ServiceInfo)
async def update_health_status(
    service_id: UUID,
    healthy: bool,
    db: AsyncSession = Depends(get_db),
) -> ServiceInfo:
    """Update service health status."""
    repo = ServiceRepository(db)

    service = await repo.update_health_status(service_id, healthy)
    if not service:
        raise HTTPException(404, f"Service {service_id} not found")

    return _convert_to_service_info(service)
