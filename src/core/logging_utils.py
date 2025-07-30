"""Utilities for structured logging."""

from collections.abc import Callable
from functools import wraps
from typing import Any, Literal

from src.core.logging import get_logger, log_event


def log_function_call(
    logger_name: str | None = None,
    log_args: bool = True,
    log_result: bool = True,
    level: str = "info",
) -> Callable:
    """Decorator to log function calls with structured data.

    Args:
        logger_name: Optional logger name (defaults to module name)
        log_args: Whether to log function arguments
        log_result: Whether to log function result
        level: Log level for the messages

    Returns:
        Decorated function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = get_logger(logger_name or func.__module__)

            # Log function entry
            event_data: dict[str, Any] = {
                "function": func.__name__,
            }

            if log_args:
                event_data["args"] = args
                event_data["kwargs"] = kwargs

            log_event(logger, "function_called", level=level, **event_data)

            try:
                # Execute function
                result = await func(*args, **kwargs)

                # Log function exit
                exit_data: dict[str, Any] = {
                    "function": func.__name__,
                    "status": "success",
                }

                if log_result:
                    exit_data["result"] = result

                log_event(logger, "function_completed", level=level, **exit_data)

                return result

            except Exception as e:
                # Log function error
                log_event(
                    logger,
                    "function_failed",
                    level="error",
                    function=func.__name__,
                    error_type=type(e).__name__,
                    error_message=str(e),
                )
                raise

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = get_logger(logger_name or func.__module__)

            # Log function entry
            event_data: dict[str, Any] = {
                "function": func.__name__,
            }

            if log_args:
                event_data["args"] = args
                event_data["kwargs"] = kwargs

            log_event(logger, "function_called", level=level, **event_data)

            try:
                # Execute function
                result = func(*args, **kwargs)

                # Log function exit
                exit_data: dict[str, Any] = {
                    "function": func.__name__,
                    "status": "success",
                }

                if log_result:
                    exit_data["result"] = result

                log_event(logger, "function_completed", level=level, **exit_data)

                return result

            except Exception as e:
                # Log function error
                log_event(
                    logger,
                    "function_failed",
                    level="error",
                    function=func.__name__,
                    error_type=type(e).__name__,
                    error_message=str(e),
                )
                raise

        # Return appropriate wrapper based on function type
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class LogContext:
    """Context manager for temporary logging context."""

    def __init__(self, logger: Any, **context: Any) -> None:
        """Initialize with logger and context to bind."""
        self.logger = logger
        self.context = context
        self.bound_logger = None

    def __enter__(self) -> Any:
        """Enter context and bind logger."""
        self.bound_logger = self.logger.bind(**self.context)
        return self.bound_logger

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> Literal[False]:
        """Exit context."""
        if exc_type:
            log_event(
                self.bound_logger or self.logger,
                "context_error",
                level="error",
                error_type=exc_type.__name__,
                error_message=str(exc_val),
            )
        return False
