"""Test structured logging functionality."""

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
    logs = capture_logs.read().strip().split('\n')
    
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
    logs = capture_logs.read().strip().split('\n')
    
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
    logs = capture_logs.read().strip().split('\n')
    
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
    logs = capture_logs.read().strip().split('\n')
    
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
    logs = capture_logs.read().strip().split('\n')
    
    # Verify context binding
    inside_log = json.loads(logs[0])
    assert inside_log["request_id"] == "req-123"
    assert inside_log["user"] == "user-456"
    
    outside_log = json.loads(logs[1])
    assert "request_id" not in outside_log
    assert "user" not in outside_log
