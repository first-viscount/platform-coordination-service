#!/usr/bin/env python3
"""Bootstrap script to enhance structured logging in the Platform Coordination Service.

This script adds structlog dependency and additional logging utilities to complement
the existing logging infrastructure.
"""

import os
import sys
from pathlib import Path

# Define the structured logging files to create
LOGGING_FILES = {
    # Core logging module
    "src/core/logging.py": '''"""Structured logging configuration using structlog."""

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
''',

    # Logging middleware
    "src/api/middleware/__init__.py": '"""API middleware."""',
    
    "src/api/middleware/logging.py": '''"""Logging middleware for FastAPI."""

import time
import uuid
from typing import Callable

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
            headers={k: v for k, v in request.headers.items() if k.lower() != "authorization"},
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
            
            return response
            
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
''',

    # Logging utilities
    "src/core/logging_utils.py": '''"""Utilities for structured logging."""

from functools import wraps
from typing import Any, Callable, Dict, Optional

from src.core.logging import get_logger, log_event


def log_function_call(
    logger_name: Optional[str] = None,
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
        async def async_wrapper(*args, **kwargs):
            logger = get_logger(logger_name or func.__module__)
            
            # Log function entry
            event_data: Dict[str, Any] = {
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
                exit_data: Dict[str, Any] = {
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
        def sync_wrapper(*args, **kwargs):
            logger = get_logger(logger_name or func.__module__)
            
            # Log function entry
            event_data: Dict[str, Any] = {
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
                exit_data: Dict[str, Any] = {
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
    
    def __init__(self, logger, **context):
        """Initialize with logger and context to bind."""
        self.logger = logger
        self.context = context
        self.bound_logger = None
        
    def __enter__(self):
        """Enter context and bind logger."""
        self.bound_logger = self.logger.bind(**self.context)
        return self.bound_logger
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        if exc_type:
            log_event(
                self.bound_logger,
                "context_error",
                level="error",
                error_type=exc_type.__name__,
                error_message=str(exc_val),
            )
        return False
''',

    # Test for logging
    "tests/test_logging.py": '''"""Test structured logging functionality."""

import json
import logging
from io import StringIO
from unittest.mock import patch

import pytest
import structlog

from src.core.logging import setup_logging, get_logger, log_event, create_request_logger
from src.core.logging_utils import log_function_call, LogContext


@pytest.fixture
def capture_logs():
    """Fixture to capture log output."""
    output = StringIO()
    
    # Setup logging with output to StringIO
    with patch("sys.stdout", output):
        setup_logging(level="DEBUG")
        yield output
        
    # Reset logging
    structlog.reset_defaults()


def test_setup_logging(capture_logs):
    """Test logging setup."""
    logger = get_logger("test")
    logger.info("test message", key="value")
    
    # Get log output
    capture_logs.seek(0)
    logs = capture_logs.read()
    
    # Parse JSON log
    log_entry = json.loads(logs.strip())
    
    # Verify log structure
    assert log_entry["event"] == "test message"
    assert log_entry["key"] == "value"
    assert log_entry["service"] == "platform-coordination-service"
    assert log_entry["environment"] == "development"
    assert "timestamp" in log_entry
    assert "level" in log_entry


def test_log_event(capture_logs):
    """Test log_event function."""
    logger = get_logger("test")
    
    # Log different levels
    log_event(logger, "info_event", level="info", data="info_data")
    log_event(logger, "error_event", level="error", data="error_data")
    
    # Get log output
    capture_logs.seek(0)
    logs = capture_logs.read().strip().split('\\n')
    
    # Verify logs
    assert len(logs) == 2
    
    info_log = json.loads(logs[0])
    assert info_log["event"] == "info_event"
    assert info_log["data"] == "info_data"
    assert info_log["level"] == "info"
    
    error_log = json.loads(logs[1])
    assert error_log["event"] == "error_event"
    assert error_log["data"] == "error_data"
    assert error_log["level"] == "error"


def test_create_request_logger(capture_logs):
    """Test request-specific logger creation."""
    logger = create_request_logger(
        correlation_id="test-correlation-id",
        user_id="user-123",
        request_path="/api/test"
    )
    
    logger.info("request log")
    
    # Get log output
    capture_logs.seek(0)
    log_entry = json.loads(capture_logs.read().strip())
    
    # Verify request context
    assert log_entry["correlation_id"] == "test-correlation-id"
    assert log_entry["user_id"] == "user-123"
    assert log_entry["request_path"] == "/api/test"


def test_log_function_decorator(capture_logs):
    """Test function logging decorator."""
    @log_function_call()
    def test_function(a, b):
        return a + b
        
    result = test_function(1, 2)
    assert result == 3
    
    # Get log output
    capture_logs.seek(0)
    logs = capture_logs.read().strip().split('\\n')
    
    # Should have entry and exit logs
    assert len(logs) == 2
    
    entry_log = json.loads(logs[0])
    assert entry_log["event"] == "function_called"
    assert entry_log["function"] == "test_function"
    assert entry_log["args"] == [1, 2]
    
    exit_log = json.loads(logs[1])
    assert exit_log["event"] == "function_completed"
    assert exit_log["function"] == "test_function"
    assert exit_log["status"] == "success"
    assert exit_log["result"] == 3


def test_log_function_decorator_error(capture_logs):
    """Test function logging decorator with error."""
    @log_function_call()
    def failing_function():
        raise ValueError("Test error")
        
    with pytest.raises(ValueError):
        failing_function()
        
    # Get log output
    capture_logs.seek(0)
    logs = capture_logs.read().strip().split('\\n')
    
    # Should have entry and error logs
    assert len(logs) == 2
    
    entry_log = json.loads(logs[0])
    assert entry_log["event"] == "function_called"
    
    error_log = json.loads(logs[1])
    assert error_log["event"] == "function_failed"
    assert error_log["error_type"] == "ValueError"
    assert error_log["error_message"] == "Test error"


async def test_async_function_decorator(capture_logs):
    """Test async function logging decorator."""
    @log_function_call()
    async def async_function(x):
        return x * 2
        
    result = await async_function(5)
    assert result == 10
    
    # Get log output
    capture_logs.seek(0)
    logs = capture_logs.read().strip().split('\\n')
    
    # Verify logs
    assert len(logs) == 2
    entry_log = json.loads(logs[0])
    assert entry_log["event"] == "function_called"
    
    exit_log = json.loads(logs[1])
    assert exit_log["event"] == "function_completed"
    assert exit_log["result"] == 10


def test_log_context(capture_logs):
    """Test LogContext context manager."""
    logger = get_logger("test")
    
    # Use context manager
    with LogContext(logger, request_id="req-123", user="user-456") as ctx_logger:
        ctx_logger.info("inside context")
        
    # Log outside context
    logger.info("outside context")
    
    # Get log output
    capture_logs.seek(0)
    logs = capture_logs.read().strip().split('\\n')
    
    # Verify context binding
    inside_log = json.loads(logs[0])
    assert inside_log["request_id"] == "req-123"
    assert inside_log["user"] == "user-456"
    
    outside_log = json.loads(logs[1])
    assert "request_id" not in outside_log
    assert "user" not in outside_log
''',
}

# Define updates to existing files
FILE_UPDATES = {
    # Update main.py to include logging middleware
    "src/main.py": {
        "old": '''"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import health
from src.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Platform Coordination Service API",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])

@app.get("/")
async def root():
    """Root endpoint."""
    return {"service": settings.app_name, "version": settings.app_version}''',
        "new": '''"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import health
from src.api.middleware.logging import LoggingMiddleware
from src.core.config import settings
from src.core.logging import setup_logging

# Setup structured logging
setup_logging(
    level=settings.log_level,
    service_name=settings.app_name,
    environment=settings.environment,
)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Platform Coordination Service API",
)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])

@app.get("/")
async def root():
    """Root endpoint."""
    return {"service": settings.app_name, "version": settings.app_version}'''
    },
    
    # Update config.py to include logging settings
    "src/core/config.py": {
        "old": '''"""Application configuration."""

from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    app_name: str = "platform-coordination-service"
    app_version: str = "0.1.0"
    
    # CORS
    cors_origins: List[str] = ["http://localhost:3000"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()''',
        "new": '''"""Application configuration."""

from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    app_name: str = "platform-coordination-service"
    app_version: str = "0.1.0"
    
    # Environment
    environment: str = "development"
    
    # Logging
    log_level: str = "INFO"
    
    # CORS
    cors_origins: List[str] = ["http://localhost:3000"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()'''
    },
    
    # Update health.py to use structured logging
    "src/api/routes/health.py": {
        "old": '''"""Health check endpoints."""

from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel

from src.core.config import settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime
    service: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        service=settings.app_name,
        version=settings.app_version,
    )''',
        "new": '''"""Health check endpoints."""

from datetime import datetime
from fastapi import APIRouter, Request
from pydantic import BaseModel

from src.core.config import settings
from src.core.logging import log_event

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime
    service: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    """Health check endpoint."""
    # Get logger from request state
    logger = getattr(request.state, "logger", None)
    
    if logger:
        log_event(
            logger,
            "health_check_requested",
            endpoint="/health",
        )
    
    response = HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        service=settings.app_name,
        version=settings.app_version,
    )
    
    if logger:
        log_event(
            logger,
            "health_check_completed",
            status="healthy",
        )
    
    return response'''
    },
}

# Define dependency updates
DEPENDENCY_UPDATES = {
    "pyproject.toml": {
        "old": '''[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.104.1"
uvicorn = {extras = ["standard"], version = "^0.24.0"}
pydantic = "^2.5.0"
pydantic-settings = "^2.1.0"''',
        "new": '''[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.104.1"
uvicorn = {extras = ["standard"], version = "^0.24.0"}
pydantic = "^2.5.0"
pydantic-settings = "^2.1.0"
structlog = "^24.1.0"'''
    }
}


def create_logging_structure():
    """Create the logging structure and update existing files."""
    base_dir = Path(__file__).parent.parent
    
    print("🚀 Starting structured logging implementation...")
    print("=" * 60)
    
    # Phase 1: Create new logging files
    print("\n📁 Phase 1: Creating new logging files...")
    created_files = []
    for file_path, content in LOGGING_FILES.items():
        full_path = base_dir / file_path
        
        # Create directory if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        full_path.write_text(content)
        created_files.append(file_path)
        print(f"  ✓ Created {file_path}")
    
    # Phase 2: Update existing files
    print(f"\n📝 Phase 2: Updating existing files...")
    updated_files = []
    for file_path, update in FILE_UPDATES.items():
        full_path = base_dir / file_path
        
        if full_path.exists():
            current_content = full_path.read_text()
            if update["old"] in current_content:
                new_content = current_content.replace(update["old"], update["new"])
                full_path.write_text(new_content)
                updated_files.append(file_path)
                print(f"  ✓ Updated {file_path}")
            else:
                print(f"  ⚠️  Could not update {file_path} - content mismatch")
        else:
            print(f"  ⚠️  File not found: {file_path}")
    
    # Phase 3: Update dependencies
    print(f"\n📦 Phase 3: Updating dependencies...")
    for file_path, update in DEPENDENCY_UPDATES.items():
        full_path = base_dir / file_path
        
        if full_path.exists():
            current_content = full_path.read_text()
            if update["old"] in current_content:
                new_content = current_content.replace(update["old"], update["new"])
                full_path.write_text(new_content)
                print(f"  ✓ Updated {file_path}")
            else:
                print(f"  ⚠️  Could not update {file_path} - content mismatch")
        else:
            print(f"  ⚠️  File not found: {file_path}")
    
    # Summary
    print("\n" + "=" * 60)
    print(f"✅ Structured logging implementation complete!")
    print(f"   - Created {len(created_files)} new files")
    print(f"   - Updated {len(updated_files)} existing files")
    print(f"   - Added 'structlog' dependency")
    
    print("\n📋 Next steps:")
    print("1. Install new dependencies: poetry install")
    print("2. Run tests to verify: make test")
    print("3. Start the service: make run")
    print("4. Check logs in JSON format on stdout")
    
    print("\n🔍 Logging features added:")
    print("   - Structured JSON logging with structlog")
    print("   - Request correlation IDs")
    print("   - Automatic request/response logging")
    print("   - Function call decorators")
    print("   - Context-aware logging")
    print("   - Environment-based configuration")


if __name__ == "__main__":
    create_logging_structure()