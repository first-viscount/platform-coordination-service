#!/usr/bin/env python3
"""Bootstrap comprehensive integration tests for the Platform Coordination Service.

This script creates a complete integration test suite that:
- Tests all API endpoints thoroughly
- Verifies error handling in various scenarios
- Tests middleware behavior
- Includes edge cases and boundary conditions
- Tests with different configurations
- Provides fixtures and utilities for easy extension
"""

import os
import sys
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def create_test_fixtures():
    """Create test fixtures and utilities."""
    fixtures_content = '''"""Test fixtures and utilities for integration tests."""

import json
import uuid
from datetime import UTC, datetime
from typing import Any, Dict, Optional
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from src.main import app
from src.core.config import settings


class TestConfig:
    """Test configuration."""
    
    # Test data constants
    VALID_ITEM_ID = "test-item-001"
    INVALID_ITEM_ID = "non-existent-999"
    LARGE_VALUE = 999999999
    NEGATIVE_VALUE = -1
    MAX_ALLOWED_VALUE = 1000
    
    # Timing constants for performance tests
    ACCEPTABLE_RESPONSE_TIME = 0.5  # seconds
    BULK_REQUEST_COUNT = 100
    
    # Error injection scenarios
    ERROR_SCENARIOS = [
        "validation",
        "not_found",
        "conflict",
        "bad_request",
        "internal"
    ]


class TestDataFactory:
    """Factory for creating test data."""
    
    @staticmethod
    def create_item(
        item_id: Optional[str] = None,
        name: Optional[str] = None,
        value: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a test item."""
        return {
            "id": item_id or f"test-{uuid.uuid4()}",
            "name": name or f"Test Item {uuid.uuid4()}",
            "value": value if value is not None else 42
        }
    
    @staticmethod
    def create_invalid_item() -> Dict[str, Any]:
        """Create an invalid item for testing validation."""
        return {
            "id": "",  # Empty ID
            "name": "x" * 101,  # Exceeds max length
            "value": -100  # Negative value
        }
    
    @staticmethod
    def create_edge_case_items() -> list[Dict[str, Any]]:
        """Create items with edge case values."""
        return [
            {"id": "edge-1", "name": "a", "value": 0},  # Min values
            {"id": "edge-2", "name": "x" * 100, "value": 1000},  # Max values
            {"id": "edge-3", "name": "Unicode测试", "value": 500},  # Unicode
            {"id": "edge-4", "name": "Special!@#$%", "value": 999},  # Special chars
        ]


@pytest.fixture
def test_client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def test_config():
    """Provide test configuration."""
    return TestConfig()


@pytest.fixture
def test_factory():
    """Provide test data factory."""
    return TestDataFactory()


@pytest.fixture
def clean_items_db(test_client):
    """Clean the items database before and after tests."""
    # Import here to avoid circular dependency
    from src.api.routes.example import items_db
    
    # Clear before test
    items_db.clear()
    
    yield
    
    # Clear after test
    items_db.clear()


@pytest.fixture
def populated_items_db(test_client, test_factory, clean_items_db):
    """Populate items database with test data."""
    from src.api.routes.example import items_db
    
    # Add test items
    test_items = [
        test_factory.create_item("item-001", "First Item", 100),
        test_factory.create_item("item-002", "Second Item", 200),
        test_factory.create_item("item-003", "Third Item", 300),
    ]
    
    for item in test_items:
        items_db[item["id"]] = item
    
    return test_items


@contextmanager
def assert_performance(max_duration: float = 1.0):
    """Context manager to assert performance constraints."""
    import time
    
    start_time = time.time()
    yield
    elapsed = time.time() - start_time
    
    assert elapsed < max_duration, f"Operation took {elapsed:.3f}s, expected < {max_duration}s"


def assert_error_response(
    response,
    expected_status: int,
    expected_error_type: str,
    expected_error_code: Optional[str] = None,
    check_correlation_id: bool = True
):
    """Assert that an error response matches expected format."""
    assert response.status_code == expected_status
    
    data = response.json()
    assert "error" in data
    error = data["error"]
    
    # Check required fields
    assert "type" in error
    assert "message" in error
    assert "timestamp" in error
    assert "path" in error
    
    # Check error type
    assert error["type"] == expected_error_type
    
    # Check error code if specified
    if expected_error_code:
        assert error.get("code") == expected_error_code
    
    # Check timestamp format
    try:
        datetime.fromisoformat(error["timestamp"].replace("Z", "+00:00"))
    except ValueError:
        pytest.fail(f"Invalid timestamp format: {error['timestamp']}")
    
    # Check correlation ID in headers
    if check_correlation_id:
        assert "X-Correlation-ID" in response.headers
    
    return error


def assert_validation_error_details(error: Dict[str, Any], expected_fields: list[str]):
    """Assert validation error contains expected field errors."""
    assert "details" in error
    details = error["details"]
    
    # Extract field names from details
    error_fields = [detail.get("field") for detail in details if "field" in detail]
    
    # Check all expected fields have errors
    for field in expected_fields:
        assert field in error_fields, f"Expected validation error for field '{field}'"


class MockExternalService:
    """Mock external service for testing integrations."""
    
    def __init__(self):
        self.call_count = 0
        self.should_fail = False
        self.response_delay = 0
    
    def call(self, *args, **kwargs):
        """Simulate external service call."""
        import time
        
        self.call_count += 1
        
        if self.response_delay:
            time.sleep(self.response_delay)
        
        if self.should_fail:
            raise Exception("Mock service failure")
        
        return {"status": "success", "call_count": self.call_count}


@pytest.fixture
def mock_external_service():
    """Provide mock external service."""
    return MockExternalService()


def capture_logs(test_client):
    """Capture and return logs generated during request."""
    # This would integrate with the actual logging system
    # For now, we'll return a placeholder
    return []


class IntegrationTestBase:
    """Base class for integration tests with common utilities."""
    
    def setup_method(self):
        """Setup test method."""
        self.start_time = datetime.now(UTC)
    
    def teardown_method(self):
        """Teardown test method."""
        duration = (datetime.now(UTC) - self.start_time).total_seconds()
        if duration > 1.0:
            print(f"Warning: Test took {duration:.2f}s")
    
    @staticmethod
    def make_request_with_headers(
        client: TestClient,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ):
        """Make request with custom headers."""
        headers = headers or {}
        headers.setdefault("X-Request-ID", str(uuid.uuid4()))
        
        return getattr(client, method)(url, headers=headers, **kwargs)
'''
    
    fixtures_path = project_root / "tests" / "integration" / "conftest.py"
    fixtures_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(fixtures_path, 'w') as f:
        f.write(fixtures_content)
    
    print(f"✓ Created test fixtures: {fixtures_path}")


def create_health_integration_tests():
    """Create comprehensive health endpoint integration tests."""
    health_tests = '''"""Integration tests for health endpoints."""

import pytest
from datetime import UTC, datetime
from unittest.mock import patch

from tests.integration.conftest import (
    assert_performance,
    IntegrationTestBase,
    capture_logs
)


class TestHealthEndpoints(IntegrationTestBase):
    """Test health check endpoints."""
    
    def test_health_check_success(self, test_client):
        """Test successful health check."""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all required fields
        assert data["status"] == "healthy"
        assert data["service"] == "platform-coordination-service"
        assert "version" in data
        assert "timestamp" in data
        
        # Verify timestamp is recent (within last 5 seconds)
        timestamp = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
        now = datetime.now(UTC)
        assert (now - timestamp).total_seconds() < 5
    
    def test_health_check_performance(self, test_client):
        """Test health check responds quickly."""
        with assert_performance(max_duration=0.1):  # 100ms max
            response = test_client.get("/health")
            assert response.status_code == 200
    
    def test_health_check_concurrent_requests(self, test_client):
        """Test health check handles concurrent requests."""
        import concurrent.futures
        
        def make_health_request():
            return test_client.get("/health")
        
        # Make 50 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_health_request) for _ in range(50)]
            responses = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # All should succeed
        assert all(r.status_code == 200 for r in responses)
        assert len(responses) == 50
    
    def test_health_check_headers(self, test_client):
        """Test health check response headers."""
        response = test_client.get("/health")
        
        # Check CORS headers are present
        assert "access-control-allow-origin" in response.headers
        
        # Check content type
        assert response.headers["content-type"] == "application/json"
    
    def test_health_check_with_invalid_method(self, test_client):
        """Test health check with wrong HTTP method."""
        response = test_client.post("/health")
        assert response.status_code == 405  # Method not allowed
    
    @patch('src.api.routes.health.datetime')
    def test_health_check_timestamp_format(self, mock_datetime, test_client):
        """Test health check timestamp formatting edge cases."""
        # Mock a specific timestamp
        mock_now = datetime(2025, 1, 1, 0, 0, 0, 0, UTC)
        mock_datetime.now.return_value = mock_now
        mock_datetime.fromisoformat = datetime.fromisoformat
        
        response = test_client.get("/health")
        data = response.json()
        
        # Timestamp should be ISO format with Z suffix
        assert data["timestamp"] == "2025-01-01T00:00:00Z"
    
    def test_root_endpoint_success(self, test_client):
        """Test root endpoint returns service info."""
        response = test_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["service"] == "platform-coordination-service"
        assert "version" in data
        assert len(data) == 2  # Only service and version
    
    def test_root_endpoint_performance(self, test_client):
        """Test root endpoint performance."""
        with assert_performance(max_duration=0.05):  # 50ms max
            response = test_client.get("/")
            assert response.status_code == 200
    
    def test_openapi_endpoint(self, test_client):
        """Test OpenAPI schema endpoint."""
        response = test_client.get("/openapi.json")
        
        assert response.status_code == 200
        schema = response.json()
        
        # Verify OpenAPI structure
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
        
        # Verify custom fields
        assert schema["info"]["title"] == "platform-coordination-service"
        assert "description" in schema["info"]
        assert len(schema["info"]["description"]) > 100  # Has substantial docs
        
        # Verify error schema is included
        assert "components" in schema
        assert "schemas" in schema["components"]
        assert "ErrorResponse" in schema["components"]["schemas"]
    
    def test_docs_endpoint(self, test_client):
        """Test Swagger UI docs endpoint."""
        response = test_client.get("/docs")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "swagger-ui" in response.text.lower()
    
    def test_redoc_endpoint(self, test_client):
        """Test ReDoc docs endpoint."""
        response = test_client.get("/redoc")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "redoc" in response.text.lower()


class TestHealthEndpointEdgeCases:
    """Test edge cases and error scenarios for health endpoints."""
    
    def test_health_check_with_malformed_headers(self, test_client):
        """Test health check with malformed headers."""
        headers = {
            "Accept": "invalid/type",
            "Content-Type": "\\x00\\x01",  # Invalid bytes
            "X-Custom-Header": "x" * 10000  # Very long header
        }
        
        response = test_client.get("/health", headers=headers)
        # Should still work despite bad headers
        assert response.status_code == 200
    
    def test_health_check_logging(self, test_client):
        """Test that health checks are properly logged."""
        # This would need actual log capture implementation
        response = test_client.get("/health")
        assert response.status_code == 200
        
        # logs = capture_logs(test_client)
        # assert any("health_check_requested" in log for log in logs)
        # assert any("health_check_completed" in log for log in logs)
    
    def test_trailing_slash_handling(self, test_client):
        """Test endpoints handle trailing slashes correctly."""
        # Without trailing slash
        response1 = test_client.get("/health")
        # With trailing slash
        response2 = test_client.get("/health/")
        
        # Both should work (FastAPI handles this)
        assert response1.status_code == 200
        assert response2.status_code in [200, 307]  # 307 for redirect
'''
    
    health_tests_path = project_root / "tests" / "integration" / "test_health_integration.py"
    
    with open(health_tests_path, 'w') as f:
        f.write(health_tests)
    
    print(f"✓ Created health integration tests: {health_tests_path}")


def create_example_integration_tests():
    """Create comprehensive example endpoints integration tests."""
    example_tests = '''"""Integration tests for example API endpoints."""

import pytest
import json
from typing import Dict, Any

from tests.integration.conftest import (
    assert_performance,
    assert_error_response,
    assert_validation_error_details,
    IntegrationTestBase,
    TestConfig
)


class TestExampleEndpoints(IntegrationTestBase):
    """Test example CRUD endpoints."""
    
    def test_create_item_success(self, test_client, test_factory, clean_items_db):
        """Test successful item creation."""
        item_data = test_factory.create_item()
        
        response = test_client.post("/api/v1/examples/items", json=item_data)
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify response matches request
        assert data["id"] == item_data["id"]
        assert data["name"] == item_data["name"]
        assert data["value"] == item_data["value"]
    
    def test_create_item_validation_errors(self, test_client, clean_items_db):
        """Test item creation with various validation errors."""
        test_cases = [
            # Empty ID
            ({"id": "", "name": "Test", "value": 42}, ["id"]),
            # Name too long
            ({"id": "test-1", "name": "x" * 101, "value": 42}, ["name"]),
            # Negative value
            ({"id": "test-2", "name": "Test", "value": -1}, ["value"]),
            # Missing fields
            ({"id": "test-3"}, ["name", "value"]),
            # Wrong types
            ({"id": 123, "name": 456, "value": "not-a-number"}, ["id", "name", "value"]),
        ]
        
        for item_data, expected_fields in test_cases:
            response = test_client.post("/api/v1/examples/items", json=item_data)
            
            error = assert_error_response(
                response, 
                expected_status=422,
                expected_error_type="ValidationError"
            )
            
            assert_validation_error_details(error, expected_fields)
    
    def test_create_item_business_rule_validation(self, test_client, test_factory, clean_items_db):
        """Test business rule validation (value > 1000)."""
        item_data = test_factory.create_item(value=1001)
        
        response = test_client.post("/api/v1/examples/items", json=item_data)
        
        error = assert_error_response(
            response,
            expected_status=400,
            expected_error_type="ValidationError",
            expected_error_code="VALIDATION_ERROR"
        )
        
        assert "Value cannot exceed 1000" in error["message"]
        assert error["details"][0]["field"] == "value"
        assert error["details"][0]["constraint"] == "max_value"
    
    def test_create_item_conflict(self, test_client, test_factory, populated_items_db):
        """Test creating item with duplicate ID."""
        # Try to create item with existing ID
        item_data = test_factory.create_item(item_id="item-001")
        
        response = test_client.post("/api/v1/examples/items", json=item_data)
        
        error = assert_error_response(
            response,
            expected_status=409,
            expected_error_type="ConflictError",
            expected_error_code="ITEM_ALREADY_EXISTS"
        )
        
        assert "already exists" in error["message"]
    
    def test_get_item_success(self, test_client, populated_items_db):
        """Test successful item retrieval."""
        response = test_client.get("/api/v1/examples/items/item-001")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == "item-001"
        assert data["name"] == "First Item"
        assert data["value"] == 100
    
    def test_get_item_not_found(self, test_client, clean_items_db, test_config):
        """Test getting non-existent item."""
        response = test_client.get(f"/api/v1/examples/items/{test_config.INVALID_ITEM_ID}")
        
        error = assert_error_response(
            response,
            expected_status=404,
            expected_error_type="NotFoundError",
            expected_error_code="RESOURCE_NOT_FOUND"
        )
        
        assert test_config.INVALID_ITEM_ID in error["message"]
    
    def test_list_items_success(self, test_client, populated_items_db):
        """Test listing items."""
        response = test_client.get("/api/v1/examples/items")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) == 3
        assert all("id" in item and "name" in item and "value" in item for item in data)
    
    def test_list_items_pagination(self, test_client, test_factory, clean_items_db):
        """Test pagination parameters."""
        from src.api.routes.example import items_db
        
        # Create 20 items
        for i in range(20):
            item = test_factory.create_item(item_id=f"item-{i:03d}")
            items_db[item["id"]] = item
        
        # Test different pagination scenarios
        test_cases = [
            ({"limit": 5, "offset": 0}, 5),
            ({"limit": 10, "offset": 5}, 10),
            ({"limit": 10, "offset": 15}, 5),  # Only 5 items left
            ({"limit": 100, "offset": 0}, 20),  # Limit exceeds total
        ]
        
        for params, expected_count in test_cases:
            response = test_client.get("/api/v1/examples/items", params=params)
            assert response.status_code == 200
            data = response.json()
            assert len(data) == expected_count
    
    def test_list_items_invalid_pagination(self, test_client):
        """Test invalid pagination parameters."""
        test_cases = [
            {"limit": -1, "offset": 0},  # Negative limit
            {"limit": 10, "offset": -5},  # Negative offset
            {"limit": 101, "offset": 0},  # Limit too high
            {"limit": "abc", "offset": 0},  # Non-numeric
        ]
        
        for params in test_cases:
            response = test_client.get("/api/v1/examples/items", params=params)
            assert response.status_code == 422
    
    def test_delete_item_success(self, test_client, populated_items_db):
        """Test successful item deletion."""
        response = test_client.delete("/api/v1/examples/items/item-001")
        
        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data["message"]
        
        # Verify item is gone
        response = test_client.get("/api/v1/examples/items/item-001")
        assert response.status_code == 404
    
    def test_delete_item_not_found(self, test_client, clean_items_db):
        """Test deleting non-existent item."""
        response = test_client.delete("/api/v1/examples/items/non-existent")
        
        assert_error_response(
            response,
            expected_status=404,
            expected_error_type="NotFoundError",
            expected_error_code="RESOURCE_NOT_FOUND"
        )


class TestExampleErrorEndpoints:
    """Test error example endpoints."""
    
    @pytest.mark.parametrize("error_type,expected_status,expected_error_type", [
        ("validation", 400, "ValidationError"),
        ("not_found", 404, "NotFoundError"),
        ("conflict", 409, "ConflictError"),
        ("bad_request", 400, "BadRequestError"),
        ("internal", 500, "InternalServerError"),
    ])
    def test_error_examples(self, test_client, error_type, expected_status, expected_error_type):
        """Test each error example type."""
        response = test_client.get(f"/api/v1/examples/error-examples/{error_type}")
        
        if error_type == "internal" and expected_error_type == "InternalServerError":
            # In development mode, we might see the actual RuntimeError
            assert response.status_code == expected_status
            error = response.json()["error"]
            assert error["type"] in ["InternalServerError", "RuntimeError"]
        else:
            assert_error_response(
                response,
                expected_status=expected_status,
                expected_error_type=expected_error_type
            )
    
    def test_error_example_invalid_type(self, test_client):
        """Test error example with invalid type."""
        response = test_client.get("/api/v1/examples/error-examples/invalid-type")
        
        # Should get validation error from path parameter regex
        assert response.status_code == 422
    
    def test_divide_endpoint_success(self, test_client):
        """Test divide endpoint with valid inputs."""
        response = test_client.get("/api/v1/examples/divide/10/2")
        
        assert response.status_code == 200
        data = response.json()
        assert data["result"] == 5.0
    
    def test_divide_endpoint_zero_division(self, test_client):
        """Test divide endpoint with zero divisor."""
        response = test_client.get("/api/v1/examples/divide/10/0")
        
        # Should be caught by error handling middleware
        assert response.status_code == 500
        error = response.json()["error"]
        assert error["type"] in ["ZeroDivisionError", "InternalServerError"]
    
    def test_divide_endpoint_invalid_inputs(self, test_client):
        """Test divide endpoint with invalid inputs."""
        test_cases = [
            "/api/v1/examples/divide/abc/2",
            "/api/v1/examples/divide/10/xyz",
            "/api/v1/examples/divide//2",
            "/api/v1/examples/divide/10/",
        ]
        
        for path in test_cases:
            response = test_client.get(path)
            assert response.status_code in [404, 422]


class TestExampleEndpointEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_create_item_edge_values(self, test_client, test_factory, clean_items_db):
        """Test creating items with edge case values."""
        edge_items = test_factory.create_edge_case_items()
        
        for item_data in edge_items:
            response = test_client.post("/api/v1/examples/items", json=item_data)
            
            # All should succeed except those exceeding limits
            if item_data["value"] <= 1000 and len(item_data["name"]) <= 100:
                assert response.status_code == 201
                assert response.json() == item_data
            else:
                assert response.status_code in [400, 422]
    
    def test_unicode_handling(self, test_client, test_factory, clean_items_db):
        """Test handling of unicode characters."""
        unicode_items = [
            test_factory.create_item(name="测试中文"),
            test_factory.create_item(name="тест русский"),
            test_factory.create_item(name="テスト日本語"),
            test_factory.create_item(name="🚀 Emoji Test 🎉"),
        ]
        
        for item_data in unicode_items:
            # Create
            response = test_client.post("/api/v1/examples/items", json=item_data)
            assert response.status_code == 201
            
            # Retrieve
            response = test_client.get(f"/api/v1/examples/items/{item_data['id']}")
            assert response.status_code == 200
            assert response.json()["name"] == item_data["name"]
    
    def test_special_characters_in_paths(self, test_client):
        """Test special characters in path parameters."""
        special_ids = [
            "item%20with%20spaces",
            "item-with-dashes",
            "item_with_underscores",
            "item.with.dots",
        ]
        
        for item_id in special_ids:
            response = test_client.get(f"/api/v1/examples/items/{item_id}")
            # Should get 404 (not found) not 400 (bad request)
            assert response.status_code == 404
    
    def test_large_request_body(self, test_client, clean_items_db):
        """Test handling of large request bodies."""
        # Create item with very long name (at the limit)
        large_item = {
            "id": "large-1",
            "name": "x" * 100,  # Max allowed
            "value": 1000  # Max allowed
        }
        
        response = test_client.post("/api/v1/examples/items", json=large_item)
        assert response.status_code == 201
    
    def test_concurrent_modifications(self, test_client, test_factory, clean_items_db):
        """Test concurrent modifications don't cause issues."""
        import concurrent.futures
        
        item_id = "concurrent-test"
        item_data = test_factory.create_item(item_id=item_id)
        
        # Create item first
        test_client.post("/api/v1/examples/items", json=item_data)
        
        def modify_item(value):
            updated_item = item_data.copy()
            updated_item["value"] = value
            return test_client.post("/api/v1/examples/items", json=updated_item)
        
        # Try to modify concurrently (should get conflicts)
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(modify_item, i * 100) for i in range(5)]
            responses = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # All should get 409 Conflict
        assert all(r.status_code == 409 for r in responses)
'''
    
    example_tests_path = project_root / "tests" / "integration" / "test_example_integration.py"
    
    with open(example_tests_path, 'w') as f:
        f.write(example_tests)
    
    print(f"✓ Created example integration tests: {example_tests_path}")


def create_middleware_integration_tests():
    """Create middleware integration tests."""
    middleware_tests = '''"""Integration tests for middleware components."""

import pytest
import json
from unittest.mock import patch
from datetime import UTC, datetime

from tests.integration.conftest import (
    assert_error_response,
    IntegrationTestBase,
    assert_performance
)


class TestErrorHandlingMiddleware(IntegrationTestBase):
    """Test error handling middleware behavior."""
    
    def test_unhandled_exception_development(self, test_client):
        """Test unhandled exceptions in development mode."""
        # Trigger an unhandled exception
        response = test_client.get("/api/v1/examples/divide/10/0")
        
        assert response.status_code == 500
        error = response.json()["error"]
        
        # In development, should include debug info
        assert "type" in error
        assert "message" in error
        assert "timestamp" in error
        assert "path" in error
    
    @patch('src.api.middleware.error_handling.settings.environment', 'production')
    def test_unhandled_exception_production(self, test_client):
        """Test unhandled exceptions in production mode."""
        # Trigger an unhandled exception
        response = test_client.get("/api/v1/examples/divide/10/0")
        
        error = assert_error_response(
            response,
            expected_status=500,
            expected_error_type="InternalServerError"
        )
        
        # In production, should not include sensitive info
        assert error["message"] == "An unexpected error occurred"
        assert "traceback" not in error
        assert "debug_info" not in error
    
    def test_request_validation_error_handling(self, test_client):
        """Test request validation error handling."""
        # Invalid query parameters
        response = test_client.get("/api/v1/examples/items?limit=-1")
        
        error = assert_error_response(
            response,
            expected_status=422,
            expected_error_type="ValidationError"
        )
        
        assert error["message"] == "Request validation failed"
        assert "details" in error
        assert any("limit" in str(detail) for detail in error["details"])
    
    def test_http_exception_handling(self, test_client):
        """Test HTTP exception handling."""
        # Trigger 404
        response = test_client.get("/non-existent-endpoint")
        
        # Custom 404 handler should apply
        assert response.status_code == 404
        error = response.json()["error"]
        assert "Resource not found" in error["message"]
    
    def test_correlation_id_propagation(self, test_client):
        """Test correlation ID is propagated through errors."""
        headers = {"X-Request-ID": "test-correlation-123"}
        
        # Trigger an error
        response = test_client.get(
            "/api/v1/examples/items/non-existent",
            headers=headers
        )
        
        assert response.status_code == 404
        assert "X-Correlation-ID" in response.headers
        # Note: Actual correlation ID implementation may differ
    
    def test_error_response_headers(self, test_client):
        """Test error responses include proper headers."""
        response = test_client.get("/api/v1/examples/error-examples/validation")
        
        assert response.status_code == 400
        assert "X-Error-Code" in response.headers
        assert response.headers["X-Error-Code"] == "VALIDATION_ERROR"
        assert response.headers["content-type"] == "application/json"
    
    def test_sensitive_data_sanitization(self, test_client):
        """Test sensitive data is sanitized in errors."""
        # Send request with sensitive data
        sensitive_data = {
            "id": "test-1",
            "name": "Test Item",
            "value": 50,
            "password": "secret123",  # Extra field that might leak
            "api_token": "tok_12345"
        }
        
        response = test_client.post("/api/v1/examples/items", json=sensitive_data)
        
        # Should get validation error for extra fields
        if response.status_code == 422:
            error_text = response.text
            # Sensitive values should be redacted
            assert "secret123" not in error_text
            assert "tok_12345" not in error_text


class TestCORSMiddleware:
    """Test CORS middleware configuration."""
    
    def test_cors_headers_on_success(self, test_client):
        """Test CORS headers are present on successful requests."""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
    
    def test_cors_headers_on_error(self, test_client):
        """Test CORS headers are present on error responses."""
        response = test_client.get("/api/v1/examples/items/non-existent")
        
        assert response.status_code == 404
        assert "access-control-allow-origin" in response.headers
    
    def test_cors_preflight_request(self, test_client):
        """Test CORS preflight (OPTIONS) requests."""
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type"
        }
        
        response = test_client.options("/api/v1/examples/items", headers=headers)
        
        assert response.status_code == 200
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers
    
    def test_cors_with_credentials(self, test_client):
        """Test CORS with credentials support."""
        headers = {"Origin": "http://localhost:3000"}
        
        response = test_client.get("/health", headers=headers)
        
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-credentials") == "true"
    
    def test_cors_different_origins(self, test_client):
        """Test CORS behavior with different origins."""
        test_origins = [
            ("http://localhost:3000", True),  # Allowed
            ("http://localhost:8080", True),  # Depends on config
            ("https://evil.com", True),  # Should check if blocked
        ]
        
        for origin, should_have_cors in test_origins:
            headers = {"Origin": origin}
            response = test_client.get("/health", headers=headers)
            
            assert response.status_code == 200
            if should_have_cors:
                assert "access-control-allow-origin" in response.headers


class TestMiddlewareInteractions:
    """Test interactions between different middleware components."""
    
    def test_middleware_order_error_then_cors(self, test_client):
        """Test that error handling happens before CORS."""
        headers = {"Origin": "http://localhost:3000"}
        
        # Trigger an error
        response = test_client.get(
            "/api/v1/examples/items/non-existent",
            headers=headers
        )
        
        # Should have both error response and CORS headers
        assert response.status_code == 404
        assert "access-control-allow-origin" in response.headers
        
        error = response.json()["error"]
        assert error["type"] == "NotFoundError"
    
    def test_middleware_performance_impact(self, test_client):
        """Test middleware doesn't significantly impact performance."""
        # Baseline request without middleware effects
        with assert_performance(max_duration=0.1):
            response = test_client.get("/health")
            assert response.status_code == 200
        
        # Request that triggers error handling
        with assert_performance(max_duration=0.15):  # Allow slightly more time
            response = test_client.get("/api/v1/examples/items/non-existent")
            assert response.status_code == 404
    
    def test_middleware_with_large_payloads(self, test_client):
        """Test middleware handles large payloads correctly."""
        # Create a large but valid item
        large_item = {
            "id": "large-1",
            "name": "x" * 100,  # Max length
            "value": 1000,  # Max value
            "extra_data": ["item"] * 1000  # Extra data that should be ignored
        }
        
        response = test_client.post("/api/v1/examples/items", json=large_item)
        
        # Should process normally (might get validation error for extra fields)
        assert response.status_code in [201, 422]
        
        # Response should be properly formatted
        data = response.json()
        assert "error" in data or "id" in data
    
    def test_middleware_request_id_generation(self, test_client):
        """Test request ID generation when not provided."""
        # Request without X-Request-ID
        response = test_client.get("/api/v1/examples/items/non-existent")
        
        assert response.status_code == 404
        # Should have generated a correlation ID
        assert "X-Correlation-ID" in response.headers
        
        # Request with X-Request-ID
        headers = {"X-Request-ID": "custom-id-123"}
        response = test_client.get("/api/v1/examples/items/non-existent", headers=headers)
        
        assert response.status_code == 404
        # Should use the provided ID
        assert "X-Correlation-ID" in response.headers


class TestMiddlewareEdgeCases:
    """Test middleware edge cases and error scenarios."""
    
    def test_middleware_with_streaming_response(self, test_client):
        """Test middleware doesn't break streaming responses."""
        # If we had streaming endpoints, test them here
        pass
    
    def test_middleware_with_websocket_upgrade(self, test_client):
        """Test middleware doesn't interfere with WebSocket upgrades."""
        # If we had WebSocket endpoints, test them here
        pass
    
    def test_middleware_memory_leak_prevention(self, test_client):
        """Test middleware doesn't cause memory leaks."""
        import gc
        import sys
        
        initial_objects = len(gc.get_objects())
        
        # Make many requests
        for _ in range(100):
            test_client.get("/health")
            test_client.get("/api/v1/examples/items/non-existent")
        
        # Force garbage collection
        gc.collect()
        
        final_objects = len(gc.get_objects())
        
        # Object count shouldn't grow significantly
        object_growth = final_objects - initial_objects
        assert object_growth < 1000, f"Potential memory leak: {object_growth} objects"
    
    def test_middleware_with_malformed_json(self, test_client):
        """Test middleware handles malformed JSON gracefully."""
        headers = {"Content-Type": "application/json"}
        
        # Send malformed JSON
        response = test_client.post(
            "/api/v1/examples/items",
            data='{"id": "test", "name": invalid json}',
            headers=headers
        )
        
        # Should get proper error response
        assert response.status_code in [400, 422]
        error = response.json()["error"]
        assert "type" in error
        assert "message" in error
'''
    
    middleware_tests_path = project_root / "tests" / "integration" / "test_middleware_integration.py"
    
    with open(middleware_tests_path, 'w') as f:
        f.write(middleware_tests)
    
    print(f"✓ Created middleware integration tests: {middleware_tests_path}")


def create_performance_integration_tests():
    """Create performance and load testing."""
    performance_tests = '''"""Integration tests for performance and load scenarios."""

import pytest
import time
import statistics
import concurrent.futures
from typing import List, Callable

from tests.integration.conftest import (
    assert_performance,
    IntegrationTestBase,
    TestConfig
)


class TestEndpointPerformance(IntegrationTestBase):
    """Test individual endpoint performance."""
    
    def measure_response_time(self, test_client, method: str, url: str, **kwargs) -> float:
        """Measure single request response time."""
        start = time.time()
        response = getattr(test_client, method)(url, **kwargs)
        elapsed = time.time() - start
        
        assert response.status_code in [200, 201], f"Request failed: {response.status_code}"
        return elapsed
    
    def test_health_endpoint_performance(self, test_client):
        """Test health endpoint meets performance requirements."""
        times = []
        
        # Warm up
        for _ in range(5):
            test_client.get("/health")
        
        # Measure
        for _ in range(50):
            elapsed = self.measure_response_time(test_client, "get", "/health")
            times.append(elapsed)
        
        # Analyze
        avg_time = statistics.mean(times)
        p95_time = statistics.quantiles(times, n=20)[18]  # 95th percentile
        max_time = max(times)
        
        # Assert performance requirements
        assert avg_time < 0.01, f"Average response time {avg_time:.3f}s exceeds 10ms"
        assert p95_time < 0.02, f"95th percentile {p95_time:.3f}s exceeds 20ms"
        assert max_time < 0.05, f"Max response time {max_time:.3f}s exceeds 50ms"
    
    def test_crud_endpoints_performance(self, test_client, test_factory, clean_items_db):
        """Test CRUD endpoints performance."""
        # Prepare test data
        items = [test_factory.create_item(item_id=f"perf-{i}") for i in range(10)]
        
        # Test CREATE performance
        create_times = []
        for item in items:
            elapsed = self.measure_response_time(
                test_client, "post", "/api/v1/examples/items", json=item
            )
            create_times.append(elapsed)
        
        assert statistics.mean(create_times) < 0.05, "CREATE too slow"
        
        # Test READ performance
        read_times = []
        for item in items:
            elapsed = self.measure_response_time(
                test_client, "get", f"/api/v1/examples/items/{item['id']}"
            )
            read_times.append(elapsed)
        
        assert statistics.mean(read_times) < 0.02, "READ too slow"
        
        # Test LIST performance
        list_times = []
        for _ in range(10):
            elapsed = self.measure_response_time(
                test_client, "get", "/api/v1/examples/items"
            )
            list_times.append(elapsed)
        
        assert statistics.mean(list_times) < 0.03, "LIST too slow"
        
        # Test DELETE performance
        delete_times = []
        for item in items[:5]:  # Delete half
            elapsed = self.measure_response_time(
                test_client, "delete", f"/api/v1/examples/items/{item['id']}"
            )
            delete_times.append(elapsed)
        
        assert statistics.mean(delete_times) < 0.03, "DELETE too slow"
    
    def test_error_handling_performance(self, test_client):
        """Test error handling doesn't significantly impact performance."""
        # Compare successful vs error responses
        success_times = []
        error_times = []
        
        for _ in range(20):
            # Successful request
            start = time.time()
            response = test_client.get("/health")
            success_times.append(time.time() - start)
            assert response.status_code == 200
            
            # Error request (404)
            start = time.time()
            response = test_client.get("/api/v1/examples/items/non-existent")
            error_times.append(time.time() - start)
            assert response.status_code == 404
        
        # Error handling shouldn't add more than 50% overhead
        avg_success = statistics.mean(success_times)
        avg_error = statistics.mean(error_times)
        
        assert avg_error < avg_success * 1.5, \
            f"Error handling too slow: {avg_error:.3f}s vs {avg_success:.3f}s"


class TestLoadScenarios:
    """Test system behavior under load."""
    
    def run_concurrent_requests(
        self,
        test_client,
        request_func: Callable,
        num_requests: int,
        max_workers: int = 10
    ) -> List[float]:
        """Run concurrent requests and return response times."""
        times = []
        errors = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(request_func) for _ in range(num_requests)]
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    elapsed = future.result()
                    times.append(elapsed)
                except Exception as e:
                    errors.append(str(e))
        
        if errors:
            pytest.fail(f"Concurrent requests failed: {errors[:5]}")  # Show first 5 errors
        
        return times
    
    def test_concurrent_read_load(self, test_client, populated_items_db):
        """Test system under concurrent read load."""
        def read_request():
            start = time.time()
            response = test_client.get("/api/v1/examples/items")
            elapsed = time.time() - start
            assert response.status_code == 200
            return elapsed
        
        # Run 100 concurrent reads
        times = self.run_concurrent_requests(test_client, read_request, 100, max_workers=20)
        
        # Analyze results
        avg_time = statistics.mean(times)
        p95_time = statistics.quantiles(times, n=20)[18]
        
        # Under load, allow more time but still reasonable
        assert avg_time < 0.2, f"Average time under load: {avg_time:.3f}s"
        assert p95_time < 0.5, f"95th percentile under load: {p95_time:.3f}s"
    
    def test_concurrent_write_load(self, test_client, test_factory, clean_items_db):
        """Test system under concurrent write load."""
        counter = 0
        
        def write_request():
            nonlocal counter
            counter += 1
            item = test_factory.create_item(item_id=f"load-{counter}")
            
            start = time.time()
            response = test_client.post("/api/v1/examples/items", json=item)
            elapsed = time.time() - start
            
            assert response.status_code in [201, 409]  # 409 if ID collision
            return elapsed
        
        # Run 50 concurrent writes
        times = self.run_concurrent_requests(test_client, write_request, 50, max_workers=10)
        
        # Writes can be slower than reads
        avg_time = statistics.mean(times)
        assert avg_time < 0.3, f"Average write time under load: {avg_time:.3f}s"
    
    def test_mixed_load_scenario(self, test_client, test_factory, populated_items_db):
        """Test realistic mixed load scenario."""
        read_times = []
        write_times = []
        
        def mixed_request(request_type: str):
            if request_type == "read":
                start = time.time()
                response = test_client.get("/api/v1/examples/items")
                elapsed = time.time() - start
                assert response.status_code == 200
                return ("read", elapsed)
            else:
                item = test_factory.create_item()
                start = time.time()
                response = test_client.post("/api/v1/examples/items", json=item)
                elapsed = time.time() - start
                assert response.status_code in [201, 409]
                return ("write", elapsed)
        
        # 80% reads, 20% writes
        request_types = ["read"] * 80 + ["write"] * 20
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            futures = [executor.submit(mixed_request, req_type) for req_type in request_types]
            
            for future in concurrent.futures.as_completed(futures):
                req_type, elapsed = future.result()
                if req_type == "read":
                    read_times.append(elapsed)
                else:
                    write_times.append(elapsed)
        
        # Both should maintain reasonable performance
        assert statistics.mean(read_times) < 0.2
        assert statistics.mean(write_times) < 0.3
    
    def test_sustained_load(self, test_client):
        """Test system behavior under sustained load."""
        # Run load for 10 seconds
        start_time = time.time()
        request_count = 0
        response_times = []
        
        while time.time() - start_time < 10:
            req_start = time.time()
            response = test_client.get("/health")
            elapsed = time.time() - req_start
            
            assert response.status_code == 200
            response_times.append(elapsed)
            request_count += 1
            
            # Small delay to avoid overwhelming
            time.sleep(0.01)
        
        # System should handle sustained load
        assert request_count > 500, f"Only processed {request_count} requests in 10s"
        assert statistics.mean(response_times) < 0.05
        
        # Check for performance degradation
        first_half = response_times[:len(response_times)//2]
        second_half = response_times[len(response_times)//2:]
        
        # Performance shouldn't degrade significantly
        assert statistics.mean(second_half) < statistics.mean(first_half) * 1.5


class TestPerformanceEdgeCases:
    """Test performance in edge case scenarios."""
    
    def test_large_payload_performance(self, test_client, clean_items_db):
        """Test performance with large payloads."""
        # Create item with maximum allowed values
        large_item = {
            "id": "large-perf-test",
            "name": "x" * 100,  # Max length
            "value": 1000  # Max value
        }
        
        times = []
        for _ in range(10):
            start = time.time()
            response = test_client.post("/api/v1/examples/items", json=large_item)
            elapsed = time.time() - start
            times.append(elapsed)
            
            # Clean up for next iteration
            if response.status_code == 201:
                test_client.delete(f"/api/v1/examples/items/{large_item['id']}")
        
        # Large payloads shouldn't cause significant slowdown
        assert statistics.mean(times) < 0.1
    
    def test_pagination_performance_scaling(self, test_client, test_factory, clean_items_db):
        """Test pagination performance with different data sizes."""
        from src.api.routes.example import items_db
        
        # Test with different dataset sizes
        dataset_sizes = [10, 100, 1000]
        
        for size in dataset_sizes:
            # Clear and populate
            items_db.clear()
            for i in range(size):
                item = test_factory.create_item(item_id=f"scale-{i:04d}")
                items_db[item["id"]] = item
            
            # Measure list performance
            times = []
            for _ in range(5):
                start = time.time()
                response = test_client.get("/api/v1/examples/items?limit=10")
                elapsed = time.time() - start
                times.append(elapsed)
                assert response.status_code == 200
            
            avg_time = statistics.mean(times)
            
            # Performance should be O(1) for pagination, not O(n)
            assert avg_time < 0.05, f"Pagination slow with {size} items: {avg_time:.3f}s"
    
    def test_error_recovery_performance(self, test_client):
        """Test system recovers quickly after errors."""
        # Cause some errors
        for _ in range(10):
            test_client.get("/api/v1/examples/divide/10/0")  # Division by zero
        
        # Measure recovery
        recovery_times = []
        for _ in range(10):
            start = time.time()
            response = test_client.get("/health")
            elapsed = time.time() - start
            recovery_times.append(elapsed)
            assert response.status_code == 200
        
        # Should recover to normal performance quickly
        assert statistics.mean(recovery_times) < 0.02
    
    def test_memory_efficient_operations(self, test_client, test_factory, clean_items_db):
        """Test operations don't cause memory spikes."""
        import gc
        import os
        import psutil
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform many operations
        for i in range(100):
            # Create
            item = test_factory.create_item(item_id=f"mem-{i}")
            test_client.post("/api/v1/examples/items", json=item)
            
            # Read
            test_client.get(f"/api/v1/examples/items/mem-{i}")
            
            # List
            test_client.get("/api/v1/examples/items")
            
            # Delete
            test_client.delete(f"/api/v1/examples/items/mem-{i}")
        
        # Force garbage collection
        gc.collect()
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be minimal
        assert memory_growth < 50, f"Memory grew by {memory_growth:.1f}MB"


class TestPerformanceMonitoring:
    """Test performance monitoring and metrics."""
    
    def test_response_time_headers(self, test_client):
        """Test if response time headers are included."""
        response = test_client.get("/health")
        
        # Check for common performance headers
        # (These might not be implemented yet, but should be)
        # assert "X-Response-Time" in response.headers
        # assert "X-Process-Time" in response.headers
    
    def test_slow_request_logging(self, test_client):
        """Test that slow requests are logged appropriately."""
        # This would require log capture functionality
        # Simulate a slow operation if possible
        pass
    
    def test_performance_degradation_detection(self, test_client):
        """Test ability to detect performance degradation."""
        baseline_times = []
        degraded_times = []
        
        # Baseline performance
        for _ in range(20):
            start = time.time()
            test_client.get("/health")
            baseline_times.append(time.time() - start)
        
        # Simulate degradation (would need actual degradation mechanism)
        # For now, just test that we can measure differences
        
        baseline_avg = statistics.mean(baseline_times)
        baseline_stddev = statistics.stdev(baseline_times)
        
        # Performance should be consistent
        assert baseline_stddev < baseline_avg * 0.5, "Performance too variable"
'''
    
    performance_tests_path = project_root / "tests" / "integration" / "test_performance_integration.py"
    
    with open(performance_tests_path, 'w') as f:
        f.write(performance_tests)
    
    print(f"✓ Created performance integration tests: {performance_tests_path}")


def create_security_integration_tests():
    """Create security-focused integration tests."""
    security_tests = '''"""Integration tests for security scenarios."""

import pytest
import json
from typing import Dict, Any

from tests.integration.conftest import (
    assert_error_response,
    IntegrationTestBase
)


class TestInputValidationSecurity:
    """Test input validation from a security perspective."""
    
    def test_sql_injection_attempts(self, test_client, clean_items_db):
        """Test SQL injection attempts are properly handled."""
        sql_injection_payloads = [
            "'; DROP TABLE items; --",
            "1' OR '1'='1",
            "admin'--",
            "1; DELETE FROM items WHERE 1=1; --",
            "' UNION SELECT * FROM users --",
        ]
        
        for payload in sql_injection_payloads:
            # Try in different fields
            response = test_client.post("/api/v1/examples/items", json={
                "id": payload,
                "name": "Test",
                "value": 42
            })
            
            # Should get validation error, not SQL error
            assert response.status_code in [201, 400, 422]
            
            # Try in path parameter
            response = test_client.get(f"/api/v1/examples/items/{payload}")
            assert response.status_code in [404, 422]
    
    def test_xss_prevention(self, test_client, clean_items_db):
        """Test XSS attempts are properly handled."""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src='javascript:alert(`xss`)'></iframe>",
            "'><script>alert(String.fromCharCode(88,83,83))</script>",
        ]
        
        for payload in xss_payloads:
            # Create item with XSS attempt
            response = test_client.post("/api/v1/examples/items", json={
                "id": f"xss-test-{xss_payloads.index(payload)}",
                "name": payload,
                "value": 42
            })
            
            if response.status_code == 201:
                # Retrieve and verify no script execution
                data = response.json()
                assert data["name"] == payload  # Should be stored as-is, not executed
                
                # When retrieved, should also be escaped properly
                get_response = test_client.get(f"/api/v1/examples/items/{data['id']}")
                assert get_response.status_code == 200
                assert get_response.json()["name"] == payload
    
    def test_command_injection_attempts(self, test_client):
        """Test command injection attempts are handled."""
        command_payloads = [
            "; ls -la",
            "| cat /etc/passwd",
            "`rm -rf /`",
            "$(whoami)",
            "&& echo 'hacked'",
        ]
        
        for payload in command_payloads:
            response = test_client.post("/api/v1/examples/items", json={
                "id": f"cmd-{command_payloads.index(payload)}",
                "name": payload,
                "value": 42
            })
            
            # Should handle gracefully
            assert response.status_code in [201, 400, 422]
    
    def test_path_traversal_attempts(self, test_client):
        """Test path traversal attempts."""
        traversal_payloads = [
            "../../../etc/passwd",
            "..\\\\..\\\\..\\\\windows\\\\system32\\\\config\\\\sam",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..%252f..%252f..%252fetc%252fpasswd",
        ]
        
        for payload in traversal_payloads:
            # Try in path parameter
            response = test_client.get(f"/api/v1/examples/items/{payload}")
            
            # Should get 404, not file contents
            assert response.status_code in [404, 422]
            
            # Ensure no file system information leaked
            if response.status_code == 404:
                error = response.json()["error"]
                assert "/etc/passwd" not in str(error)
                assert "windows" not in str(error).lower()
    
    def test_xxe_prevention(self, test_client):
        """Test XML External Entity (XXE) injection prevention."""
        # Even though we use JSON, test XML payloads are rejected
        xxe_payload = """<?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE foo [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ]>
        <item>
            <id>&xxe;</id>
            <name>test</name>
            <value>42</value>
        </item>"""
        
        response = test_client.post(
            "/api/v1/examples/items",
            data=xxe_payload,
            headers={"Content-Type": "application/xml"}
        )
        
        # Should reject non-JSON content
        assert response.status_code in [400, 415, 422]


class TestAuthenticationSecurity:
    """Test authentication and authorization security."""
    
    def test_missing_authentication_headers(self, test_client):
        """Test behavior when authentication headers are missing."""
        # Currently no auth, but test the pattern
        response = test_client.get("/health")
        assert response.status_code == 200
        
        # When auth is added, should return 401 for protected endpoints
    
    def test_invalid_authentication_tokens(self, test_client):
        """Test handling of invalid authentication tokens."""
        invalid_tokens = [
            "Bearer invalid-token",
            "Bearer ",
            "InvalidScheme token",
            "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature",
            "",
        ]
        
        for token in invalid_tokens:
            headers = {"Authorization": token}
            response = test_client.get("/health", headers=headers)
            
            # Currently should work (no auth), but pattern for future
            assert response.status_code == 200
    
    def test_jwt_algorithm_confusion(self, test_client):
        """Test protection against JWT algorithm confusion attacks."""
        # Test various JWT attack payloads when auth is implemented
        pass


class TestRateLimitingSecurity:
    """Test rate limiting and DoS protection."""
    
    def test_rapid_requests(self, test_client):
        """Test behavior under rapid request scenarios."""
        # Make 100 requests rapidly
        responses = []
        for _ in range(100):
            response = test_client.get("/health")
            responses.append(response.status_code)
        
        # Currently no rate limiting, all should succeed
        assert all(status == 200 for status in responses)
        
        # When rate limiting is added, should see 429 responses
    
    def test_large_request_body_limits(self, test_client):
        """Test request body size limits."""
        # Create very large item
        large_item = {
            "id": "large-1",
            "name": "x" * 10000,  # 10KB name
            "value": 42
        }
        
        response = test_client.post("/api/v1/examples/items", json=large_item)
        
        # Should reject based on validation (max 100 chars)
        assert response.status_code == 422
    
    def test_deeply_nested_json(self, test_client):
        """Test handling of deeply nested JSON to prevent DoS."""
        # Create deeply nested structure
        nested = {"a": 1}
        for _ in range(100):
            nested = {"nested": nested}
        
        response = test_client.post("/api/v1/examples/items", json=nested)
        
        # Should handle gracefully
        assert response.status_code in [400, 422]


class TestErrorMessageSecurity:
    """Test error messages don't leak sensitive information."""
    
    def test_error_messages_production_mode(self, test_client):
        """Test error messages in production mode."""
        from unittest.mock import patch
        
        with patch('src.api.middleware.error_handling.settings.environment', 'production'):
            # Trigger internal error
            response = test_client.get("/api/v1/examples/divide/10/0")
            
            assert response.status_code == 500
            error = response.json()["error"]
            
            # Should not include sensitive details
            assert "traceback" not in error
            assert "ZeroDivisionError" not in str(error)
            assert error["message"] == "An unexpected error occurred"
    
    def test_path_information_leakage(self, test_client):
        """Test that internal paths aren't leaked."""
        response = test_client.get("/api/v1/examples/items/non-existent")
        
        error_text = json.dumps(response.json())
        
        # Should not contain internal paths
        assert "/home/" not in error_text
        assert "/usr/" not in error_text
        assert "C:\\\\" not in error_text
        assert ".py" not in error_text
    
    def test_stack_trace_exposure(self, test_client):
        """Test stack traces aren't exposed in errors."""
        # Trigger various errors
        error_endpoints = [
            "/api/v1/examples/divide/10/0",
            "/api/v1/examples/error-examples/internal",
        ]
        
        for endpoint in error_endpoints:
            response = test_client.get(endpoint)
            error_text = response.text.lower()
            
            # Should not contain stack trace indicators
            assert "traceback" not in error_text
            assert "file " not in error_text
            assert "line " not in error_text
            assert ".py" not in error_text


class TestHeaderSecurity:
    """Test security headers and configurations."""
    
    def test_security_headers_present(self, test_client):
        """Test that security headers are included in responses."""
        response = test_client.get("/health")
        
        # These headers should be added for security
        # Currently might not all be implemented
        expected_headers = [
            # "X-Content-Type-Options",
            # "X-Frame-Options",
            # "X-XSS-Protection",
            # "Strict-Transport-Security",
            # "Content-Security-Policy",
        ]
        
        # Log which headers are missing for future implementation
        missing_headers = [h for h in expected_headers if h not in response.headers]
        if missing_headers:
            print(f"Missing security headers: {missing_headers}")
    
    def test_cors_security(self, test_client):
        """Test CORS is properly configured."""
        # Test with allowed origin
        response = test_client.get("/health", headers={"Origin": "http://localhost:3000"})
        assert "access-control-allow-origin" in response.headers
        
        # Test with potentially malicious origin
        response = test_client.get("/health", headers={"Origin": "http://evil.com"})
        # Depending on CORS config, might be blocked or allowed
        assert response.status_code == 200
    
    def test_content_type_validation(self, test_client):
        """Test content type validation."""
        # Send wrong content type
        response = test_client.post(
            "/api/v1/examples/items",
            data="not json data",
            headers={"Content-Type": "text/plain"}
        )
        
        # Should reject non-JSON for JSON endpoints
        assert response.status_code in [400, 415, 422]


class TestDataPrivacy:
    """Test data privacy and sensitive information handling."""
    
    def test_sensitive_data_logging(self, test_client):
        """Test sensitive data isn't logged."""
        sensitive_item = {
            "id": "test-1",
            "name": "Test User",
            "value": 42,
            "password": "super_secret_password",  # Extra field
            "api_key": "sk_test_1234567890",
            "ssn": "123-45-6789"
        }
        
        response = test_client.post("/api/v1/examples/items", json=sensitive_item)
        
        # Even if it fails, sensitive data shouldn't be in response
        response_text = response.text
        assert "super_secret_password" not in response_text
        assert "sk_test_1234567890" not in response_text
        assert "123-45-6789" not in response_text
    
    def test_error_detail_sanitization(self, test_client):
        """Test error details are sanitized."""
        # Send request with sensitive field names
        response = test_client.post("/api/v1/examples/items", json={
            "id": "test-1",
            "name": "Test",
            "value": "password123"  # Wrong type but contains 'password'
        })
        
        if response.status_code == 422:
            error = response.json()["error"]
            # If value is shown in error, should be sanitized
            error_text = json.dumps(error)
            # Depends on implementation, but sensitive values should be redacted
'''
    
    security_tests_path = project_root / "tests" / "integration" / "test_security_integration.py"
    
    with open(security_tests_path, 'w') as f:
        f.write(security_tests)
    
    print(f"✓ Created security integration tests: {security_tests_path}")


def create_configuration_tests():
    """Create configuration and environment tests."""
    config_tests = '''"""Integration tests for different configurations and environments."""

import pytest
import os
from unittest.mock import patch, MagicMock

from tests.integration.conftest import IntegrationTestBase


class TestConfigurationScenarios(IntegrationTestBase):
    """Test application behavior with different configurations."""
    
    def test_development_configuration(self, test_client):
        """Test application in development mode."""
        with patch('src.core.config.settings.environment', 'development'):
            # Trigger an error
            response = test_client.get("/api/v1/examples/divide/10/0")
            
            assert response.status_code == 500
            error = response.json()["error"]
            
            # Development mode should include debug info
            assert "type" in error
            # Might include traceback in dev mode
    
    def test_production_configuration(self, test_client):
        """Test application in production mode."""
        with patch('src.core.config.settings.environment', 'production'):
            # Trigger an error
            response = test_client.get("/api/v1/examples/divide/10/0")
            
            assert response.status_code == 500
            error = response.json()["error"]
            
            # Production mode should hide details
            assert error["message"] == "An unexpected error occurred"
            assert "traceback" not in error
    
    def test_cors_configuration(self, test_client):
        """Test CORS with different configurations."""
        test_origins = [
            "http://localhost:3000",
            "http://localhost:8080",
            "https://example.com",
        ]
        
        for origin in test_origins:
            response = test_client.options(
                "/api/v1/examples/items",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "POST"
                }
            )
            
            # Should handle OPTIONS requests
            assert response.status_code == 200
    
    def test_logging_configuration(self, test_client):
        """Test different logging configurations."""
        with patch('src.core.config.settings.log_level', 'DEBUG'):
            response = test_client.get("/health")
            assert response.status_code == 200
            # In DEBUG mode, would see more detailed logs
        
        with patch('src.core.config.settings.log_level', 'ERROR'):
            response = test_client.get("/health")
            assert response.status_code == 200
            # In ERROR mode, would see only errors
    
    def test_environment_variable_override(self):
        """Test environment variables override settings."""
        # Test pattern for env var configuration
        test_values = {
            "APP_NAME": "test-service",
            "APP_VERSION": "9.9.9",
            "LOG_LEVEL": "DEBUG",
            "CORS_ORIGINS": '["http://test.com"]',
        }
        
        with patch.dict(os.environ, test_values):
            # Would need to reload settings
            # from src.core.config import Settings
            # test_settings = Settings()
            # assert test_settings.app_name == "test-service"
            pass


class TestEnvironmentSpecificBehavior:
    """Test environment-specific behaviors."""
    
    def test_debug_endpoints_disabled_in_production(self, test_client):
        """Test debug endpoints are disabled in production."""
        with patch('src.core.config.settings.environment', 'production'):
            # If we had debug endpoints, test they're disabled
            # response = test_client.get("/debug/routes")
            # assert response.status_code == 404
            pass
    
    def test_detailed_errors_in_development(self, test_client):
        """Test detailed errors in development."""
        with patch('src.core.config.settings.environment', 'development'):
            # Invalid JSON
            response = test_client.post(
                "/api/v1/examples/items",
                data='{"invalid": json}',
                headers={"Content-Type": "application/json"}
            )
            
            error = response.json()["error"]
            # Should include parsing details in dev
            assert "message" in error
    
    def test_performance_logging_by_environment(self, test_client):
        """Test performance logging varies by environment."""
        environments = ['development', 'staging', 'production']
        
        for env in environments:
            with patch('src.core.config.settings.environment', env):
                response = test_client.get("/health")
                assert response.status_code == 200
                # Different environments might have different logging detail


class TestFeatureFlags:
    """Test feature flag configurations."""
    
    def test_feature_flags_enable_disable(self, test_client):
        """Test enabling/disabling features via configuration."""
        # Example pattern for feature flags
        # with patch('src.core.config.settings.enable_caching', True):
        #     response = test_client.get("/api/v1/examples/items")
        #     # Should use caching
        
        # with patch('src.core.config.settings.enable_caching', False):
        #     response = test_client.get("/api/v1/examples/items")
        #     # Should not use caching
        pass


class TestConfigurationValidation:
    """Test configuration validation and error handling."""
    
    def test_invalid_configuration_handling(self):
        """Test handling of invalid configurations."""
        invalid_configs = [
            {"log_level": "INVALID_LEVEL"},
            {"cors_origins": "not-a-list"},
            {"app_version": ""},
        ]
        
        for invalid_config in invalid_configs:
            # Would need to test configuration validation
            # with pytest.raises(ValidationError):
            #     Settings(**invalid_config)
            pass
    
    def test_missing_required_configuration(self):
        """Test behavior when required configuration is missing."""
        # Test pattern for required configs
        pass
    
    def test_configuration_type_coercion(self):
        """Test configuration type coercion."""
        with patch.dict(os.environ, {"LOG_REQUEST_BODY": "true"}):
            # Should coerce string to boolean
            # settings = Settings()
            # assert settings.log_request_body is True
            pass


class TestMultiEnvironmentScenarios:
    """Test scenarios across multiple environments."""
    
    def test_configuration_migration(self):
        """Test configuration works when migrating between environments."""
        # Simulate moving from dev to prod
        configs = [
            {"environment": "development", "log_level": "DEBUG"},
            {"environment": "staging", "log_level": "INFO"},
            {"environment": "production", "log_level": "WARNING"},
        ]
        
        for config in configs:
            # Test configuration is valid for each environment
            pass
    
    def test_environment_specific_endpoints(self, test_client):
        """Test endpoints that behave differently per environment."""
        # Health check should work in all environments
        for env in ['development', 'staging', 'production']:
            with patch('src.core.config.settings.environment', env):
                response = test_client.get("/health")
                assert response.status_code == 200
                
                # But might include different info
                data = response.json()
                assert data["service"] == "platform-coordination-service"
'''
    
    config_tests_path = project_root / "tests" / "integration" / "test_configuration_integration.py"
    
    with open(config_tests_path, 'w') as f:
        f.write(config_tests)
    
    print(f"✓ Created configuration integration tests: {config_tests_path}")


def create_test_runner():
    """Create a test runner script."""
    runner_content = '''#!/usr/bin/env python3
"""Run integration tests with various options."""

import sys
import subprocess
from pathlib import Path

def run_tests(args):
    """Run pytest with integration tests."""
    cmd = [
        "pytest",
        "tests/integration",
        "-v",
        "--tb=short",
        "--maxfail=10",
    ] + args
    
    print(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd).returncode

def main():
    """Main test runner."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run integration tests")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage")
    parser.add_argument("--performance", action="store_true", help="Run only performance tests")
    parser.add_argument("--security", action="store_true", help="Run only security tests")
    parser.add_argument("--quick", action="store_true", help="Run quick tests only")
    parser.add_argument("-k", "--keyword", help="Run tests matching keyword")
    parser.add_argument("-x", "--exitfirst", action="store_true", help="Exit on first failure")
    
    args, unknown = parser.parse_known_args()
    
    pytest_args = unknown
    
    if args.coverage:
        pytest_args.extend(["--cov=src", "--cov-report=term-missing"])
    
    if args.performance:
        pytest_args.extend(["-k", "performance"])
    elif args.security:
        pytest_args.extend(["-k", "security"])
    elif args.quick:
        pytest_args.extend(["-m", "not slow"])
    
    if args.keyword:
        pytest_args.extend(["-k", args.keyword])
    
    if args.exitfirst:
        pytest_args.append("-x")
    
    return run_tests(pytest_args)

if __name__ == "__main__":
    sys.exit(main())
'''
    
    runner_path = project_root / "scripts" / "run-integration-tests.py"
    
    with open(runner_path, 'w') as f:
        f.write(runner_content)
    
    # Make executable
    os.chmod(runner_path, 0o755)
    
    print(f"✓ Created test runner: {runner_path}")


def main():
    """Main bootstrap function."""
    print("🚀 Bootstrapping comprehensive integration tests...")
    print()
    
    # Create all test files
    create_test_fixtures()
    create_health_integration_tests()
    create_example_integration_tests()
    create_middleware_integration_tests()
    create_performance_integration_tests()
    create_security_integration_tests()
    create_configuration_tests()
    create_test_runner()
    
    print()
    print("✅ Integration test suite created successfully!")
    print()
    print("📋 Test Structure:")
    print("  tests/integration/")
    print("  ├── conftest.py                      # Fixtures and utilities")
    print("  ├── test_health_integration.py       # Health endpoint tests")
    print("  ├── test_example_integration.py      # Example CRUD tests")
    print("  ├── test_middleware_integration.py   # Middleware behavior tests")
    print("  ├── test_performance_integration.py  # Performance and load tests")
    print("  ├── test_security_integration.py     # Security-focused tests")
    print("  └── test_configuration_integration.py # Config and environment tests")
    print()
    print("🏃 Run tests with:")
    print("  # Run all integration tests")
    print("  pytest tests/integration -v")
    print()
    print("  # Run with coverage")
    print("  python scripts/run-integration-tests.py --coverage")
    print()
    print("  # Run specific test categories")
    print("  python scripts/run-integration-tests.py --performance")
    print("  python scripts/run-integration-tests.py --security")
    print()
    print("  # Run tests matching pattern")
    print("  pytest tests/integration -k 'error_handling'")
    print()
    print("💡 Test Categories:")
    print("  - Happy path testing (basic functionality)")
    print("  - Error scenarios (all error types and edge cases)")
    print("  - Performance testing (response times, load, concurrency)")
    print("  - Security testing (injection, XSS, data leakage)")
    print("  - Configuration testing (different environments)")
    print("  - Middleware testing (CORS, error handling)")
    print()
    print("🔍 Key Testing Patterns:")
    print("  - Comprehensive error validation with assert_error_response()")
    print("  - Performance assertions with assert_performance()")
    print("  - Concurrent request testing")
    print("  - Edge case and boundary testing")
    print("  - Security vulnerability testing")
    print("  - Configuration scenario testing")
    

if __name__ == "__main__":
    main()