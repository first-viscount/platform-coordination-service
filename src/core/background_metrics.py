"""Background tasks for updating metrics."""

import asyncio

from sqlalchemy import func, select

from ..models.service import Service, ServiceStatus, ServiceType
from .database import get_db_context
from .logging import get_logger
from .metrics import get_metrics_collector

logger = get_logger(__name__)


class BackgroundMetricsUpdater:
    """Background service to update metrics that require database queries."""

    def __init__(self, update_interval: int = 30) -> None:
        """Initialize the background metrics updater.

        Args:
            update_interval: Interval in seconds between metric updates
        """
        self.update_interval = update_interval
        self.metrics = get_metrics_collector()
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the background metrics update task."""
        if self._running:
            logger.warning("Background metrics updater is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._update_loop())
        logger.info("Background metrics updater started", interval=self.update_interval)

    async def stop(self) -> None:
        """Stop the background metrics update task."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Background metrics updater stopped")

    async def _update_loop(self) -> None:
        """Main update loop for background metrics."""
        while self._running:
            try:
                await self._update_active_services_metrics()
                await asyncio.sleep(self.update_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error updating background metrics", error=str(e))
                await asyncio.sleep(self.update_interval)

    async def _update_active_services_metrics(self) -> None:
        """Update active services count metrics."""
        try:
            async with get_db_context() as session:
                # Query service counts by type and status
                stmt = select(
                    Service.type, Service.status, func.count(Service.id).label("count")
                ).group_by(Service.type, Service.status)

                result = await session.execute(stmt)
                service_counts = result.all()

                # Reset all gauges to zero first
                for service_type in ServiceType:
                    for status in ServiceStatus:
                        self.metrics.update_active_services_count(
                            service_type.value, status.value, 0
                        )

                # Update with actual counts
                for service_type, status, count in service_counts:
                    self.metrics.update_active_services_count(
                        service_type.value, status.value, count
                    )

                logger.debug(
                    "Updated active services metrics",
                    total_types_statuses=len(service_counts),
                )

        except Exception as e:
            logger.error("Failed to update active services metrics", error=str(e))


# Global instance
_background_updater: BackgroundMetricsUpdater | None = None


async def start_background_metrics() -> None:
    """Start the background metrics updater."""
    global _background_updater
    if _background_updater is None:
        _background_updater = BackgroundMetricsUpdater()
    await _background_updater.start()


async def stop_background_metrics() -> None:
    """Stop the background metrics updater."""
    global _background_updater
    if _background_updater:
        await _background_updater.stop()
