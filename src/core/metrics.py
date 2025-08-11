"""Prometheus metrics configuration and collectors."""

import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry, REGISTRY
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger

logger = get_logger(__name__)

# Custom registry for our service
service_registry = CollectorRegistry()

# Service Registration Metrics
service_registrations_total = Counter(
    "service_registrations_total",
    "Total number of service registrations",
    ["service_type", "status"],
    registry=service_registry,
)

service_registration_duration_seconds = Histogram(
    "service_registration_duration_seconds",
    "Time taken to register a service",
    ["service_type"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=service_registry,
)

active_services = Gauge(
    "active_services",
    "Current number of active services",
    ["service_type", "status"],
    registry=service_registry,
)

# Query Performance Metrics
service_query_duration_seconds = Histogram(
    "service_query_duration_seconds",
    "Time taken to query services",
    ["query_type", "status"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
    registry=service_registry,
)

service_discovery_requests_total = Counter(
    "service_discovery_requests_total",
    "Total number of service discovery requests",
    ["service_name", "status"],
    registry=service_registry,
)

# Database Pool Metrics
db_pool_size = Gauge(
    "db_pool_size",
    "Current database connection pool size",
    registry=service_registry,
)

db_pool_checked_out_connections = Gauge(
    "db_pool_checked_out_connections", 
    "Number of active database connections",
    registry=service_registry,
)

db_pool_overflow = Gauge(
    "db_pool_overflow",
    "Number of overflow database connections",
    registry=service_registry,
)

db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query execution time",
    ["operation", "table"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
    registry=service_registry,
)

# HTTP Request Metrics (these will be managed by instrumentator middleware)
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
    registry=service_registry,
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=service_registry,
)

# Error Metrics
service_errors_total = Counter(
    "service_errors_total",
    "Total service errors",
    ["error_type", "endpoint"],
    registry=service_registry,
)


class MetricsCollector:
    """Centralized metrics collection and management."""

    def __init__(self) -> None:
        """Initialize the metrics collector."""
        self.start_time = time.time()
        logger.info("Metrics collector initialized")

    def record_service_registration(
        self, service_type: str, duration: float, success: bool = True
    ) -> None:
        """Record service registration metrics."""
        status = "success" if success else "error"
        service_registrations_total.labels(
            service_type=service_type, status=status
        ).inc()
        service_registration_duration_seconds.labels(service_type=service_type).observe(
            duration
        )

    def update_active_services_count(
        self, service_type: str, status: str, count: int
    ) -> None:
        """Update the count of active services."""
        active_services.labels(service_type=service_type, status=status).set(count)

    def record_service_query(
        self, query_type: str, duration: float, success: bool = True
    ) -> None:
        """Record service query metrics."""
        status = "success" if success else "error"
        service_query_duration_seconds.labels(
            query_type=query_type, status=status
        ).observe(duration)

    def record_service_discovery(
        self, service_name: str, found: bool = True
    ) -> None:
        """Record service discovery request."""
        status = "found" if found else "not_found"
        service_discovery_requests_total.labels(
            service_name=service_name, status=status
        ).inc()

    def record_database_query(
        self, operation: str, table: str, duration: float
    ) -> None:
        """Record database query metrics."""
        db_query_duration_seconds.labels(operation=operation, table=table).observe(
            duration
        )

    def update_db_pool_metrics(
        self, pool_size: int, checked_out: int, overflow: int
    ) -> None:
        """Update database pool metrics."""
        db_pool_size.set(pool_size)
        db_pool_checked_out_connections.set(checked_out)
        db_pool_overflow.set(overflow)

    def record_error(self, error_type: str, endpoint: str) -> None:
        """Record service errors."""
        service_errors_total.labels(error_type=error_type, endpoint=endpoint).inc()

    @asynccontextmanager
    async def timed_operation(
        self, operation_type: str, **labels: Any
    ) -> AsyncGenerator[None, None]:
        """Context manager for timing operations."""
        start_time = time.time()
        try:
            yield
        except Exception as e:
            self.record_error(type(e).__name__, operation_type)
            raise
        finally:
            duration = time.time() - start_time
            if operation_type == "service_registration":
                self.record_service_registration(
                    labels.get("service_type", "unknown"), duration
                )
            elif operation_type == "service_query":
                self.record_service_query(
                    labels.get("query_type", "unknown"), duration
                )
            elif operation_type == "database_query":
                self.record_database_query(
                    labels.get("operation", "unknown"),
                    labels.get("table", "unknown"),
                    duration,
                )


# Global metrics collector instance
metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    return metrics_collector


@asynccontextmanager
async def db_metrics_context(
    session: AsyncSession, operation: str, table: str
) -> AsyncGenerator[None, None]:
    """Context manager for database operations with metrics."""
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        metrics_collector.record_database_query(operation, table, duration)
        
        # Update connection pool metrics if available
        if hasattr(session.get_bind(), "pool"):
            pool = session.get_bind().pool
            metrics_collector.update_db_pool_metrics(
                pool_size=pool.size(),
                checked_out=pool.checkedout(),
                overflow=pool.overflow(),
            )