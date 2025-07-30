"""Structured logging configuration using structlog with thread-safe context management."""

import logging
import sys
from contextvars import ContextVar
from typing import Any

import structlog
from structlog.stdlib import filter_by_level

# Thread-safe context variables
_request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)
_correlation_id_context: ContextVar[str | None] = ContextVar(
    "correlation_id", default=None
)
_user_id_context: ContextVar[str | None] = ContextVar("user_id", default=None)


def setup_logging(
    level: str = "INFO",
    service_name: str = "platform-coordination-service",
    environment: str = "development",
    correlation_id: str | None = None,
) -> None:
    """Configure structured logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        service_name: Name of the service for log identification
        environment: Current environment (development, staging, production)
        correlation_id: Optional correlation ID for request tracking
    """
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper()),
    )

    # Shared processors for all log entries
    shared_processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Add context processors
    context_processors = []

    # Add service metadata
    context_processors.append(
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            ]
        )
    )

    # Add custom context including thread-safe request context
    def add_custom_context(
        logger: Any, method_name: str, event_dict: dict[str, Any]
    ) -> dict[str, Any]:
        """Add custom context to all log entries."""
        event_dict["service"] = service_name
        event_dict["environment"] = environment

        # Add thread-safe context values
        if req_id := get_request_id():
            event_dict["request_id"] = req_id
        if corr_id := get_correlation_id():
            event_dict["correlation_id"] = corr_id
        if user_id := get_user_id():
            event_dict["user_id"] = user_id

        # Legacy correlation_id parameter (for backward compatibility)
        if correlation_id and "correlation_id" not in event_dict:
            event_dict["correlation_id"] = correlation_id

        return event_dict

    context_processors.append(add_custom_context)  # type: ignore[arg-type]

    # Configure structlog
    structlog.configure(
        processors=[
            filter_by_level,
            *shared_processors,  # type: ignore[list-item]
            *context_processors,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a configured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)  # type: ignore[no-any-return]


def log_event(
    logger: structlog.stdlib.BoundLogger, event: str, level: str = "info", **kwargs: Any
) -> None:
    """Log a structured event with additional context.

    Args:
        logger: Logger instance
        event: Event description
        level: Log level
        **kwargs: Additional structured data
    """
    log_method = getattr(logger, level.lower())
    log_method(event, **kwargs)


def create_request_logger(
    correlation_id: str,
    user_id: str | None = None,
    request_path: str | None = None,
) -> structlog.stdlib.BoundLogger:
    """Create a logger bound with request-specific context.

    Args:
        correlation_id: Request correlation ID
        user_id: Optional user identifier
        request_path: Optional request path

    Returns:
        Logger with bound request context
    """
    logger = get_logger("request")

    # Bind request context
    logger = logger.bind(correlation_id=correlation_id)

    if user_id:
        logger = logger.bind(user_id=user_id)

    if request_path:
        logger = logger.bind(request_path=request_path)

    return logger


# Thread-safe context management functions for request tracking
def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID in the logging context."""
    _correlation_id_context.set(correlation_id)


def get_correlation_id() -> str | None:
    """Get the current correlation ID from the logging context."""
    return _correlation_id_context.get()


def set_request_id(request_id: str) -> None:
    """Set the request ID in the logging context."""
    _request_id_context.set(request_id)


def get_request_id() -> str | None:
    """Get the current request ID from the logging context."""
    return _request_id_context.get()


def set_user_id(user_id: str) -> None:
    """Set the user ID in the logging context."""
    _user_id_context.set(user_id)


def get_user_id() -> str | None:
    """Get the current user ID from the logging context."""
    return _user_id_context.get()


def clear_context() -> None:
    """Clear the logging context."""
    _request_id_context.set(None)
    _correlation_id_context.set(None)
    _user_id_context.set(None)
