"""Service repository implementation."""

import builtins
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from ..core.exceptions import ConflictError
from ..core.logging import get_logger
from ..core.metrics import db_metrics_context, get_metrics_collector
from ..models.service import Service, ServiceEvent, ServiceStatus
from .base import BaseRepository

logger = get_logger(__name__)
metrics = get_metrics_collector()


class ServiceRepository(BaseRepository[Service]):
    """Repository for service registry operations."""

    async def create(self, **kwargs: Any) -> Service:
        """Create a new service registration."""
        async with db_metrics_context(self.session, "create", "services"):
            try:
                service = Service(**kwargs)
                self.session.add(service)

                await self.session.commit()
                await self.session.refresh(service)

                # Record service registration metrics
                service_type = kwargs.get("type", "unknown")
                if hasattr(service_type, "value"):
                    service_type = service_type.value
                metrics.record_service_registration(str(service_type), 0, success=True)

                # Create event in a separate transaction to avoid flush issues
                try:
                    async with db_metrics_context(
                        self.session, "create", "service_events"
                    ):
                        event = ServiceEvent(
                            service_id=service.id,
                            event_type="service_registered",
                            event_data={
                                "service_name": service.name,
                                "host": service.host,
                                "port": service.port,
                            },
                        )
                        self.session.add(event)
                        await self.session.commit()
                except Exception as e:
                    # Log error but don't fail the service creation
                    logger.error("Failed to create service event", error=str(e))

                logger.info(
                    "Service registered",
                    service_id=str(service.id),
                    service_name=service.name,
                    host=service.host,
                    port=service.port,
                )
                return service
            except IntegrityError as e:
                await self.session.rollback()
                service_type = kwargs.get("type", "unknown")
                if hasattr(service_type, "value"):
                    service_type = service_type.value
                metrics.record_service_registration(str(service_type), 0, success=False)
                logger.error("Service registration failed - duplicate", error=str(e))
                raise ConflictError(
                    "Service already exists with this name, host, and port"
                ) from e

    async def get(self, id: UUID, for_update: bool = False) -> Service | None:
        """Get service by ID."""
        async with db_metrics_context(self.session, "select", "services"):
            stmt = select(Service).where(Service.id == id)
            if for_update:
                stmt = stmt.with_for_update()
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_by_name_host_port(
        self, name: str, host: str, port: int
    ) -> Service | None:
        """Get service by unique endpoint combination."""
        stmt = select(Service).where(
            and_(Service.name == name, Service.host == host, Service.port == port)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, id: UUID, **kwargs: Any) -> Service | None:
        """Update service with optimistic locking."""
        service = await self.get(id)
        if not service:
            return None

        # Check version for optimistic locking
        expected_version = kwargs.pop("version", None)
        if expected_version is not None and service.version != expected_version:
            raise ConflictError("Service was modified by another process")

        # Track status changes
        old_status = service.status
        new_status = kwargs.get("status")

        # Update fields
        for key, value in kwargs.items():
            setattr(service, key, value)

        service.last_seen_at = datetime.now(UTC)
        service.version = service.version + 1

        # Log status change event
        if new_status and old_status != new_status:
            event = ServiceEvent(
                service_id=service.id,
                event_type="status_change",
                event_data={
                    "old_status": old_status.value,
                    "new_status": new_status.value,
                },
            )
            self.session.add(event)

        await self.session.commit()
        await self.session.refresh(service)

        logger.info(
            "Service updated",
            service_id=str(service.id),
            service_name=service.name,
            changes=list(kwargs.keys()),
        )
        return service

    async def delete(self, id: UUID) -> bool:
        """Delete service (soft delete by setting status)."""
        service = await self.get(id)
        if not service:
            return False

        # Log deletion event
        event = ServiceEvent(
            service_id=service.id,
            event_type="service_unregistered",
            event_data={"service_name": service.name},
        )
        self.session.add(event)

        # Actually delete the service (cascade will delete events)
        await self.session.delete(service)
        await self.session.commit()

        logger.info(
            "Service unregistered",
            service_id=str(id),
            service_name=service.name,
        )
        return True

    async def list(
        self,
        **filters: Any,
    ) -> list[Service]:
        """List services with optional filters."""
        async with db_metrics_context(self.session, "select", "services"):
            # Extract specific filters
            type = filters.get("type")
            status = filters.get("status")
            tag_key = filters.get("tag_key")
            tag_value = filters.get("tag_value")
            include_events = filters.get("include_events", False)

            stmt = select(Service)

            # Apply filters
            if type:
                stmt = stmt.where(Service.type == type)
            if status:
                stmt = stmt.where(Service.status == status)
            if tag_key and tag_value:
                # PostgreSQL JSON query - extract and compare text
                from sqlalchemy import text

                stmt = stmt.where(
                    text("service_metadata->'tags'->>:tag_key = :tag_value").bindparams(
                        tag_key=tag_key, tag_value=tag_value
                    )
                )

            # Include events if requested
            if include_events:
                stmt = stmt.options(selectinload(Service.events))

            # Order by name for consistent results
            stmt = stmt.order_by(Service.name)

            result = await self.session.execute(stmt)
            services = list(result.scalars().all())

            # Record query metrics
            metrics.record_service_query("list", 0, success=True)

            return services

    async def find_by_name(
        self,
        name: str,
        status: ServiceStatus | None = None,
        exclude_unhealthy: bool = True,
    ) -> builtins.list[Service]:
        """Find services by name with optional status filter."""
        async with db_metrics_context(self.session, "select", "services"):
            stmt = select(Service).where(Service.name == name)

            if status:
                stmt = stmt.where(Service.status == status)
            elif exclude_unhealthy:
                # By default, exclude unhealthy services
                stmt = stmt.where(Service.status != ServiceStatus.UNHEALTHY)

            stmt = stmt.order_by(Service.last_seen_at.desc())

            result = await self.session.execute(stmt)
            services = list(result.scalars().all())

            # Record service discovery metrics
            metrics.record_service_discovery(name, len(services) > 0)

            return services

    async def update_health_status(
        self, id: UUID, healthy: bool, check_time: datetime | None = None
    ) -> Service | None:
        """Update service health check status."""
        service = await self.get(id, for_update=True)
        if not service:
            return None

        # Track old status for event logging
        old_status = service.status

        if healthy:
            service.status = ServiceStatus.HEALTHY
            service.health_check_failures = 0
        else:
            service.health_check_failures = service.health_check_failures + 1
            if service.health_check_failures >= 3:
                service.status = ServiceStatus.UNHEALTHY
            else:
                service.status = ServiceStatus.DEGRADED

        service.last_health_check_at = check_time or datetime.now(UTC)
        service.last_seen_at = datetime.now(UTC)
        service.version = service.version + 1

        # Log status change event if status changed
        if old_status != service.status:
            event = ServiceEvent(
                service_id=service.id,
                event_type="status_change",
                event_data={
                    "old_status": old_status.value,
                    "new_status": service.status.value,
                },
            )
            self.session.add(event)

        await self.session.commit()
        await self.session.refresh(service)

        logger.info(
            "Health check updated",
            service_id=str(service.id),
            service_name=service.name,
            healthy=healthy,
            status=service.status.value,
        )
        return service

    async def cleanup_stale_services(self, stale_after_seconds: int = 300) -> int:
        """Remove services that haven't been seen recently."""
        cutoff_time = datetime.now(UTC).timestamp() - stale_after_seconds

        stmt = (
            delete(Service)
            .where(Service.last_seen_at < datetime.fromtimestamp(cutoff_time, UTC))
            .returning(Service.id)
        )

        result = await self.session.execute(stmt)
        deleted_ids = result.scalars().all()
        await self.session.commit()

        if deleted_ids:
            logger.info(
                "Cleaned up stale services",
                count=len(deleted_ids),
                stale_after_seconds=stale_after_seconds,
            )

        return len(deleted_ids)
