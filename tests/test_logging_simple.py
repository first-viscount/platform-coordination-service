"""Simplified tests for structured logging functionality."""

import json
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.core.logging import (
    set_request_id,
    get_request_id,
    set_correlation_id,
    get_correlation_id,
    clear_context,
)


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestLoggingContext:
    """Test logging context functions."""
    
    def test_request_id_context(self):
        """Test request ID context management."""
        # Initially should be None
        clear_context()
        assert get_request_id() is None
        
        # Set request ID
        request_id = "test-request-123"
        set_request_id(request_id)
        assert get_request_id() == request_id
        
        # Clear context
        clear_context()
        assert get_request_id() is None
    
    def test_correlation_id_context(self):
        """Test correlation ID context management."""
        # Initially should be None
        clear_context()
        assert get_correlation_id() is None
        
        # Set correlation ID
        correlation_id = "test-correlation-456"
        set_correlation_id(correlation_id)
        assert get_correlation_id() == correlation_id
        
        # Clear context
        clear_context()
        assert get_correlation_id() is None
    
    def test_auto_generate_ids(self):
        """Test automatic ID generation."""
        clear_context()
        
        # Request ID should be generated if not provided
        request_id = set_request_id()
        assert request_id is not None
        assert len(request_id) == 36  # UUID format
        
        # Correlation ID should be generated if not provided
        correlation_id = set_correlation_id()
        assert correlation_id is not None
        assert len(correlation_id) == 36  # UUID format
        
        clear_context()


class TestLoggingMiddleware:
    """Test logging middleware functionality."""
    
    def test_request_id_header_propagation(self, client):
        """Test that request ID from header is propagated."""
        request_id = "client-request-123"
        response = client.get("/health", headers={"X-Request-ID": request_id})
        
        assert response.status_code == 200
        assert response.headers.get("X-Request-ID") == request_id
    
    def test_correlation_id_header_propagation(self, client):
        """Test that correlation ID from header is propagated."""
        correlation_id = "client-correlation-456"
        response = client.get("/health", headers={"X-Correlation-ID": correlation_id})
        
        assert response.status_code == 200
        assert response.headers.get("X-Correlation-ID") == correlation_id
    
    def test_auto_generated_ids(self, client):
        """Test that IDs are auto-generated if not provided."""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        assert "X-Correlation-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) == 36
        assert len(response.headers["X-Correlation-ID"]) == 36


class TestEndpointResponses:
    """Test that endpoints work correctly with logging."""
    
    def test_health_endpoint(self, client):
        """Test that health endpoint returns correct response."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "service" in data
        assert "version" in data
    
    def test_root_endpoint(self, client):
        """Test that root endpoint returns correct response."""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert "service" in data
        assert "version" in data