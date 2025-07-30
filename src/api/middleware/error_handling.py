"""Error handling middleware for FastAPI."""

import sys
import traceback
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.config import settings
from src.core.exceptions import PlatformCoordinationError
from src.core.logging import log_event
from src.core.models.errors import ErrorDetail, ErrorResponse


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware to handle all exceptions and return structured error responses."""

    def __init__(self, app: Any, **kwargs: Any) -> None:
        super().__init__(app, **kwargs)
        self.include_debug_info = settings.environment == "development"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and handle any exceptions."""
        try:
            response = await call_next(request)
            return response  # type: ignore[no-any-return]
        except Exception as exc:
            return await self.handle_exception(request, exc)

    async def handle_exception(self, request: Request, exc: Exception) -> JSONResponse:
        """Handle different types of exceptions and return appropriate error responses."""
        # Get logger and correlation ID from request state
        logger = getattr(request.state, "logger", None)
        correlation_id = getattr(request.state, "correlation_id", None)

        # Determine error details based on exception type
        if isinstance(exc, PlatformCoordinationError):
            error_response = self._handle_platform_error(exc, request, correlation_id)
        elif isinstance(exc, RequestValidationError):
            error_response = self._handle_validation_error(exc, request, correlation_id)
        elif isinstance(exc, HTTPException | StarletteHTTPException):
            error_response = self._handle_http_exception(exc, request, correlation_id)
        elif isinstance(exc, PydanticValidationError):
            error_response = self._handle_pydantic_validation_error(
                exc, request, correlation_id
            )
        else:
            error_response = self._handle_unexpected_error(exc, request, correlation_id)

        # Log the error if we have a logger
        if logger:
            log_event(
                logger,
                "error_handled",
                level="error",
                error_type=type(exc).__name__,
                error_message=str(exc),
                status_code=error_response.status_code,
                error_code=error_response.error,
            )

        # Return JSON response
        content = error_response.model_dump(exclude_none=True)
        # Timestamp is already serialized to ISO format by the field serializer

        return JSONResponse(
            status_code=error_response.status_code,
            content=content,
            headers={
                "X-Correlation-ID": correlation_id or "",
                "X-Error-Code": error_response.error,
            },
        )

    def _handle_platform_error(
        self,
        exc: PlatformCoordinationError,
        request: Request,
        correlation_id: str | None,
    ) -> ErrorResponse:
        """Handle custom platform errors."""
        error_response = ErrorResponse(
            error=exc.error_code,
            message=exc.message,
            correlation_id=correlation_id,
            path=str(request.url.path),
            status_code=exc.status_code,
            details=None,
            debug_info=None,
            traceback=None,
        )

        # Add details if available
        if exc.details:
            error_response.details = [
                ErrorDetail(**detail) if isinstance(detail, dict) else detail
                for detail in exc.details
            ]

        # Add debug info in development
        if self.include_debug_info:
            error_response.debug_info = {
                "context": exc.context,
                "exception_type": type(exc).__name__,
            }
            error_response.traceback = traceback.format_exception(*sys.exc_info())

        return error_response

    def _handle_validation_error(
        self,
        exc: RequestValidationError,
        request: Request,
        correlation_id: str | None,
    ) -> ErrorResponse:
        """Handle FastAPI request validation errors."""
        details = []

        for error in exc.errors():
            # Extract field path
            field = ".".join(str(loc) for loc in error.get("loc", []))

            # Create validation error detail
            detail = ErrorDetail(
                field=field,
                message=error.get("msg", "Validation failed"),
                code=error.get("type", "validation_error"),
            )

            details.append(detail)

        error_response = ErrorResponse(
            error="ValidationError",
            message="Request validation failed",
            details=details,
            correlation_id=correlation_id,
            path=str(request.url.path),
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            debug_info=None,
            traceback=None,
        )

        if self.include_debug_info:
            error_response.traceback = traceback.format_exception(*sys.exc_info())

        return error_response

    def _handle_http_exception(
        self,
        exc: HTTPException | StarletteHTTPException,
        request: Request,
        correlation_id: str | None,
    ) -> ErrorResponse:
        """Handle FastAPI/Starlette HTTP exceptions."""
        error_response = ErrorResponse(
            error=f"HTTP{exc.status_code}",
            message=exc.detail if isinstance(exc.detail, str) else str(exc.detail),
            correlation_id=correlation_id,
            path=str(request.url.path),
            status_code=exc.status_code,
            details=None,
            debug_info=None,
            traceback=None,
        )

        # Add headers if available
        if hasattr(exc, "headers") and exc.headers:
            if self.include_debug_info:
                error_response.debug_info = {"headers": dict(exc.headers)}

        return error_response

    def _handle_pydantic_validation_error(
        self,
        exc: PydanticValidationError,
        request: Request,
        correlation_id: str | None,
    ) -> ErrorResponse:
        """Handle Pydantic validation errors."""
        details = []

        for error in exc.errors():
            detail = ErrorDetail(
                field=".".join(str(loc) for loc in error.get("loc", [])),
                message=error.get("msg", "Validation failed"),
                code=error.get("type", "validation_error"),
            )
            details.append(detail)

        error_response = ErrorResponse(
            error="DataValidationError",
            message="Data validation failed",
            details=details,
            correlation_id=correlation_id,
            path=str(request.url.path),
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            debug_info=None,
            traceback=None,
        )

        if self.include_debug_info:
            error_response.traceback = traceback.format_exception(*sys.exc_info())

        return error_response

    def _handle_unexpected_error(
        self, exc: Exception, request: Request, correlation_id: str | None
    ) -> ErrorResponse:
        """Handle unexpected errors."""
        # In production, hide internal details
        if not self.include_debug_info:
            return ErrorResponse(
                error="InternalServerError",
                message="An unexpected error occurred",
                correlation_id=correlation_id,
                path=str(request.url.path),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details=None,
                debug_info=None,
                traceback=None,
            )

        # In development, include full error details
        return ErrorResponse(
            error=type(exc).__name__,
            message=str(exc),
            correlation_id=correlation_id,
            path=str(request.url.path),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=None,
            debug_info={
                "exception_type": type(exc).__name__,
                "exception_module": type(exc).__module__,
            },
            traceback=traceback.format_exception(*sys.exc_info()),
        )

    def _sanitize_value(self, value: Any) -> Any:
        """Sanitize values to remove sensitive information."""
        # Don't include values that might contain passwords or tokens
        if isinstance(value, str):
            lower_value = value.lower()
            sensitive_patterns = ["password", "token", "secret", "key", "auth"]
            if any(pattern in lower_value for pattern in sensitive_patterns):
                return "[REDACTED]"

        # Truncate long values
        if isinstance(value, str) and len(value) > 100:
            return value[:100] + "..."

        return value


def create_exception_handlers(app: FastAPI) -> None:
    """Create specific exception handlers for common scenarios."""
    from fastapi import Request
    from fastapi.responses import JSONResponse

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle request validation errors."""
        middleware = ErrorHandlingMiddleware(app)
        return await middleware.handle_exception(request, exc)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        """Handle HTTP exceptions."""
        middleware = ErrorHandlingMiddleware(app)
        return await middleware.handle_exception(request, exc)

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc: Any) -> JSONResponse:
        """Handle 404 errors with custom response."""
        correlation_id = getattr(request.state, "correlation_id", None)

        error_response = ErrorResponse(
            error="NotFound",
            message=f"Resource not found: {request.url.path}",
            correlation_id=correlation_id,
            path=str(request.url.path),
            status_code=404,
            details=None,
            debug_info=None,
            traceback=None,
        )

        content = error_response.model_dump(exclude_none=True)
        # Timestamp is already serialized to ISO format by the field serializer

        return JSONResponse(
            status_code=404,
            content=content,
            headers={"X-Correlation-ID": correlation_id or ""},
        )

    @app.exception_handler(500)
    async def internal_error_handler(request: Request, exc: Any) -> JSONResponse:
        """Handle 500 errors with custom response."""
        correlation_id = getattr(request.state, "correlation_id", None)

        error_response = ErrorResponse(
            error="InternalServerError",
            message="Internal server error",
            correlation_id=correlation_id,
            path=str(request.url.path),
            status_code=500,
            details=None,
            debug_info=None,
            traceback=None,
        )

        content = error_response.model_dump(exclude_none=True)
        # Timestamp is already serialized to ISO format by the field serializer

        return JSONResponse(
            status_code=500,
            content=content,
            headers={"X-Correlation-ID": correlation_id or ""},
        )
