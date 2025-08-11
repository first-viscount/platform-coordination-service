"""HTTP metrics middleware for Prometheus monitoring."""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.logging import get_logger
from src.core.metrics import http_requests_total, http_request_duration_seconds

logger = get_logger(__name__)


class HTTPMetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP request metrics."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process HTTP request and collect metrics."""
        start_time = time.time()
        
        # Extract route pattern or use path
        endpoint = self._get_endpoint_label(request)
        method = request.method

        response = None
        status_code = "500"  # Default to server error
        
        try:
            response = await call_next(request)
            status_code = str(response.status_code)
            return response
        except Exception as e:
            logger.error(
                "Request processing error",
                method=method,
                endpoint=endpoint,
                error=str(e),
            )
            status_code = "500"
            raise
        finally:
            # Record metrics
            duration = time.time() - start_time
            
            # Record request count
            http_requests_total.labels(
                method=method, endpoint=endpoint, status_code=status_code
            ).inc()
            
            # Record request duration
            http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(
                duration
            )
            
            # Log slow requests
            if duration > 1.0:
                logger.warning(
                    "Slow request detected",
                    method=method,
                    endpoint=endpoint,
                    duration=duration,
                    status_code=status_code,
                )

    def _get_endpoint_label(self, request: Request) -> str:
        """Extract endpoint label for metrics."""
        # Try to get the route pattern
        if hasattr(request, "scope") and request.scope.get("route"):
            route = request.scope["route"]
            if hasattr(route, "path"):
                return route.path
        
        # Fallback to request path, but normalize common patterns
        path = request.url.path
        
        # Normalize paths with UUIDs or IDs
        import re
        
        # Replace UUIDs with {id}
        path = re.sub(
            r'/[a-f0-9]{8}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{12}',
            '/{id}',
            path,
            flags=re.IGNORECASE
        )
        
        # Replace numeric IDs with {id}
        path = re.sub(r'/\d+', '/{id}', path)
        
        # Limit to prevent cardinality explosion
        if len(path) > 100:
            path = path[:100] + "..."
            
        return path


def setup_http_metrics_middleware() -> type[HTTPMetricsMiddleware]:
    """Create and configure HTTP metrics middleware."""
    logger.info("Setting up HTTP metrics middleware")
    return HTTPMetricsMiddleware