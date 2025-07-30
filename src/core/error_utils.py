"""Error handling utilities and helpers."""

from typing import Any


def raise_not_found(
    resource: str, identifier: Any, context: dict[str, Any] | None = None
) -> None:
    """Raise a standardized not found error.

    Args:
        resource: Type of resource (e.g., "user", "service")
        identifier: Resource identifier
        context: Additional context
    """
    from src.core.exceptions import NotFoundError

    raise NotFoundError(
        f"{resource.capitalize()} with ID '{identifier}' not found",
        error_code=f"{resource.upper()}_NOT_FOUND",
        context=context or {},
    )


def raise_validation_error(
    message: str,
    field: str | None = None,
    details: list[dict[str, Any]] | None = None,
) -> None:
    """Raise a standardized validation error.

    Args:
        message: Error message
        field: Field that failed validation
        details: Additional error details
    """
    from src.core.exceptions import ValidationError

    error_details = details or []
    if field:
        error_details.insert(
            0,
            {
                "field": field,
                "message": message,
            },
        )

    raise ValidationError(message=message, details=error_details)


def raise_conflict(
    resource: str, message: str, context: dict[str, Any] | None = None
) -> None:
    """Raise a standardized conflict error.

    Args:
        resource: Type of resource
        message: Conflict description
        context: Additional context
    """
    from src.core.exceptions import ConflictError

    raise ConflictError(
        message=message,
        error_code=f"{resource.upper()}_CONFLICT",
        context=context or {},
    )


def handle_database_error(exc: Exception) -> None:
    """Convert database errors to appropriate HTTP errors.

    Args:
        exc: Database exception
    """
    from src.core.exceptions import ConflictError, InternalServerError

    # Handle specific database errors
    error_message = str(exc).lower()

    if "duplicate" in error_message or "unique constraint" in error_message:
        raise ConflictError("Resource already exists", error_code="DUPLICATE_RESOURCE")
    elif "foreign key" in error_message:
        from src.core.exceptions import ValidationError

        raise ValidationError(
            "Referenced resource does not exist", error_code="INVALID_REFERENCE"
        )
    elif "connection" in error_message or "timeout" in error_message:
        from src.core.exceptions import ServiceUnavailableError

        raise ServiceUnavailableError(
            "Database connection error", error_code="DATABASE_UNAVAILABLE"
        )
    else:
        # Generic database error
        raise InternalServerError(
            "Database operation failed",
            error_code="DATABASE_ERROR",
            context={"original_error": type(exc).__name__},
        )


def create_error_response_examples() -> dict[int, dict[str, Any]]:
    """Create OpenAPI response examples for common errors.

    Returns:
        Dictionary of status codes to response examples
    """
    return {
        400: {
            "description": "Bad Request",
            "content": {
                "application/json": {
                    "example": {
                        "error": "BadRequest",
                        "message": "Invalid request parameters",
                        "correlation_id": "123e4567-e89b-12d3-a456-426614174000",
                        "timestamp": "2024-01-01T12:00:00Z",
                        "path": "/api/v1/services",
                        "status_code": 400,
                    }
                }
            },
        },
        401: {
            "description": "Unauthorized",
            "content": {
                "application/json": {
                    "example": {
                        "error": "Unauthorized",
                        "message": "Authentication required",
                        "correlation_id": "123e4567-e89b-12d3-a456-426614174000",
                        "timestamp": "2024-01-01T12:00:00Z",
                        "path": "/api/v1/services",
                        "status_code": 401,
                    }
                }
            },
        },
        403: {
            "description": "Forbidden",
            "content": {
                "application/json": {
                    "example": {
                        "error": "Forbidden",
                        "message": "Insufficient permissions",
                        "correlation_id": "123e4567-e89b-12d3-a456-426614174000",
                        "timestamp": "2024-01-01T12:00:00Z",
                        "path": "/api/v1/services",
                        "status_code": 403,
                    }
                }
            },
        },
        404: {
            "description": "Not Found",
            "content": {
                "application/json": {
                    "example": {
                        "error": "NotFound",
                        "message": "Service with ID 'service-123' not found",
                        "correlation_id": "123e4567-e89b-12d3-a456-426614174000",
                        "timestamp": "2024-01-01T12:00:00Z",
                        "path": "/api/v1/services/service-123",
                        "status_code": 404,
                    }
                }
            },
        },
        422: {
            "description": "Validation Error",
            "content": {
                "application/json": {
                    "example": {
                        "error": "ValidationError",
                        "message": "Request validation failed",
                        "details": [
                            {
                                "field": "name",
                                "message": "Field required",
                                "code": "missing",
                            }
                        ],
                        "correlation_id": "123e4567-e89b-12d3-a456-426614174000",
                        "timestamp": "2024-01-01T12:00:00Z",
                        "path": "/api/v1/services",
                        "status_code": 422,
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error",
            "content": {
                "application/json": {
                    "example": {
                        "error": "InternalServerError",
                        "message": "An unexpected error occurred",
                        "correlation_id": "123e4567-e89b-12d3-a456-426614174000",
                        "timestamp": "2024-01-01T12:00:00Z",
                        "path": "/api/v1/services",
                        "status_code": 500,
                    }
                }
            },
        },
    }
