"""Middleware for the Platform Coordination Service."""

import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.logging import (
    clear_context,
    get_correlation_id,
    get_logger,
    get_request_id,
    set_correlation_id,
    set_request_id,
)

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured logging of HTTP requests."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and add logging."""
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        set_request_id(request_id)

        # Generate or extract correlation ID for distributed tracing
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        set_correlation_id(correlation_id)

        # Start timing
        start_time = time.time()

        # Log request
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            query_params=dict(request.query_params),
            client_host=request.client.host if request.client else None,
            headers={
                k: v
                for k, v in request.headers.items()
                if k.lower() not in ["authorization", "cookie"]
            },
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Log response
            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
            )

            # Add tracking headers to response
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Correlation-ID"] = correlation_id

            return response  # type: ignore[no-any-return]

        except Exception as e:
            # Calculate duration
            duration = time.time() - start_time

            # Log error
            logger.error(
                "request_failed",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration * 1000, 2),
                error=str(e),
                exc_info=True,
            )
            raise
        finally:
            # Clear context
            clear_context()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Lightweight middleware for just adding request IDs."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add request ID to context and response headers."""
        # Set request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        set_request_id(request_id)

        # Set correlation ID
        correlation_id = request.headers.get("X-Correlation-ID", request_id)
        set_correlation_id(correlation_id)

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = get_request_id() or ""
            response.headers["X-Correlation-ID"] = get_correlation_id() or ""
            return response  # type: ignore[no-any-return]
        finally:
            clear_context()
