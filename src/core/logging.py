"""Structured logging configuration using structlog."""

import sys
import logging
from typing import Any, Dict, Optional

import structlog
from structlog.stdlib import filter_by_level


def setup_logging(
    level: str = "INFO",
    service_name: str = "platform-coordination-service",
    environment: str = "development",
    correlation_id: Optional[str] = None,
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
    
    # Add custom context
    def add_custom_context(logger, method_name, event_dict):
        """Add custom context to all log entries."""
        event_dict["service"] = service_name
        event_dict["environment"] = environment
        if correlation_id:
            event_dict["correlation_id"] = correlation_id
        return event_dict
    
    context_processors.append(add_custom_context)
    
    # Configure structlog
    structlog.configure(
        processors=[
            filter_by_level,
            *shared_processors,
            *context_processors,
            structlog.processors.JSONRenderer()
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
    return structlog.get_logger(name)


def log_event(
    logger: structlog.stdlib.BoundLogger,
    event: str,
    level: str = "info",
    **kwargs: Any
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
    user_id: Optional[str] = None,
    request_path: Optional[str] = None,
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
