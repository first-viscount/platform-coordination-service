"""Logging middleware for FastAPI."""

import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.logging import create_request_logger, log_event


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests and responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and log details."""
        # Generate correlation ID
        correlation_id = str(uuid.uuid4())

        # Create request-specific logger
        logger = create_request_logger(
            correlation_id=correlation_id,
            request_path=str(request.url.path),
        )

        # Store logger in request state
        request.state.logger = logger
        request.state.correlation_id = correlation_id

        # Log request
        log_event(
            logger,
            "request_started",
            method=request.method,
            path=str(request.url.path),
            query_params=dict(request.query_params),
            headers={
                k: v for k, v in request.headers.items() if k.lower() != "authorization"
            },
        )

        # Time the request
        start_time = time.time()

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log response
            log_event(
                logger,
                "request_completed",
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )

            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id

            return response  # type: ignore[no-any-return]

        except Exception as e:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log error
            log_event(
                logger,
                "request_failed",
                level="error",
                error_type=type(e).__name__,
                error_message=str(e),
                duration_ms=round(duration_ms, 2),
            )

            # Re-raise the exception
            raise
