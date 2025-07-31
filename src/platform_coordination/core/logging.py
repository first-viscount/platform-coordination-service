"""Structured logging configuration."""

import logging
import sys
from typing import Any

import structlog
from structlog.stdlib import BoundLogger

from src.platform_coordination.core.config import settings


def setup_logging() -> BoundLogger:
    """Configure structured logging for the application."""

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )

    # Configure structlog
    timestamper = structlog.processors.TimeStamper(fmt="iso")

    shared_processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.contextvars.merge_contextvars,
    ]

    renderer: Any
    if settings.log_format == "json":
        # JSON output for production
        renderer = structlog.processors.JSONRenderer()
    else:
        # Human-readable output for development
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=shared_processors + [renderer],  # type: ignore[arg-type]
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger()  # type: ignore[no-any-return]


def get_logger(name: str | None = None) -> BoundLogger:
    """Get a logger instance."""
    return structlog.get_logger(name)  # type: ignore[no-any-return]
