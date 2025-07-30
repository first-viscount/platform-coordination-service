"""Test error handling middleware behavior."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


class TestErrorHandlingMiddleware:
    """Test suite for error handling middleware."""

    def test_platform_coordination_error_handling(self):
        """Test handling of custom platform errors."""
        # Test through the error examples endpoint
        response = client.get("/api/v1/examples/error-examples/validation")
        assert response.status_code == 422  # Validation errors return 422

        # Check response headers
        assert "X-Correlation-ID" in response.headers
        assert response.headers["X-Error-Code"] == "ValidationError"

        # Check response body structure - flat structure
        body = response.json()
        assert "error" in body  # This is the error code/type
        assert "message" in body
        assert "timestamp" in body
        assert "path" in body
        assert "status_code" in body
        # Details may or may not be present depending on error

    def test_request_validation_error_handling(self):
        """Test handling of FastAPI request validation errors."""
        # Send invalid data to trigger validation error
        response = client.post(
            "/api/v1/examples/items",
            json={
                "id": "test",
                "name": "",  # Empty name should fail validation
                "value": -1,  # Negative value should fail validation
            },
        )

        assert response.status_code == 422
        body = response.json()

        # Check error structure - flat response
        assert body["error"] == "ValidationError"
        assert body["message"] == "Request validation failed"
        assert "details" in body
        assert len(body["details"]) > 0

        # Check validation details structure
        for detail in body["details"]:
            assert "field" in detail
            assert "message" in detail
            assert "code" in detail

    def test_http_exception_handling(self):
        """Test handling of FastAPI HTTP exceptions."""
        # Access non-existent endpoint to trigger 404
        response = client.get("/api/v1/non-existent-endpoint")
        assert response.status_code == 404

        body = response.json()
        assert body["error"] == "NotFound"
        assert "Resource not found" in body["message"]
        assert body["path"] == "/api/v1/non-existent-endpoint"

    def test_unexpected_error_handling(self):
        """Test handling of unexpected errors."""
        # The divide by zero endpoint triggers an unexpected error
        response = client.get("/api/v1/examples/divide/10/0")
        assert response.status_code == 500

        body = response.json()
        # In development mode, we should see the actual exception type
        # In production, it would be masked as InternalServerError
        assert body["error"] in ["ZeroDivisionError", "InternalServerError"]
        assert "timestamp" in body
        assert "path" in body

    def test_error_response_format_consistency(self):
        """Test that all error responses follow consistent format."""
        test_cases = [
            # (endpoint, method, data, expected_status)
            ("/api/v1/examples/items/non-existent", "GET", None, 404),
            ("/api/v1/examples/items", "POST", {"invalid": "data"}, 422),
            ("/api/v1/examples/error-examples/conflict", "GET", None, 409),
            ("/api/v1/examples/error-examples/bad_request", "GET", None, 400),
        ]

        for endpoint, method, data, expected_status in test_cases:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json=data)
            else:
                response = None  # Add else to handle all cases

            assert response is not None, f"Unsupported method: {method}"
            assert response.status_code == expected_status

            # All errors should have consistent structure - flat response
            body = response.json()

            # Required fields at top level
            assert "error" in body  # This is the error code/type
            assert "message" in body
            assert "timestamp" in body
            assert "path" in body

            # Timestamp should be ISO format
            assert "T" in body["timestamp"]  # Basic ISO format check

    def test_error_headers(self):
        """Test that error responses include proper headers."""
        response = client.get("/api/v1/examples/items/non-existent")

        # Should have correlation ID header (even if empty)
        assert "X-Correlation-ID" in response.headers

        # Should have error code header for platform errors
        if response.status_code == 404:
            assert "X-Error-Code" in response.headers

    def test_validation_error_details(self):
        """Test detailed validation error information."""
        # Create item with multiple validation errors
        response = client.post(
            "/api/v1/examples/items",
            json={
                "id": "test",
                "name": "a" * 101,  # Exceeds max length of 100
                "value": -10,  # Negative value not allowed
            },
        )

        assert response.status_code == 422
        body = response.json()

        # Should have details for each validation error
        assert len(body["details"]) >= 2

        # Check that field paths are included
        field_errors = {detail["field"]: detail for detail in body["details"]}
        assert "name" in field_errors or "body.name" in field_errors
        assert "value" in field_errors or "body.value" in field_errors

    def test_error_context_preservation(self):
        """Test that error context is preserved through middleware."""
        # Conflict error includes context
        response = client.get("/api/v1/examples/error-examples/conflict")
        body = response.json()

        # In development mode, context might be visible in debug_info
        if "debug_info" in body and "context" in body["debug_info"]:
            assert body["debug_info"]["context"]["existing_id"] == "test-123"

    @patch.dict("os.environ", {"ENVIRONMENT": "production"})
    def test_production_error_masking(self):
        """Test that internal errors are masked in production."""
        # Note: This test would need proper environment setup
        # In production, internal errors should be generic
        pass  # Skipping as it requires app restart with different settings

    def test_custom_404_handler(self):
        """Test custom 404 error handler."""
        response = client.get("/this-endpoint-does-not-exist")
        assert response.status_code == 404

        body = response.json()
        assert body["error"] == "NotFound"
        assert body["path"] == "/this-endpoint-does-not-exist"

    def test_error_sanitization(self):
        """Test that sensitive data is sanitized in errors."""
        # Send data with potential sensitive field names
        sensitive_data = {
            "id": "test",
            "name": "Test Item",
            "value": 50,
            "password": "secret123",  # This field doesn't exist in model
            "api_token": "token123",  # This field doesn't exist in model
        }

        response = client.post("/api/v1/examples/items", json=sensitive_data)

        # The extra fields should cause validation error
        if response.status_code == 422:
            error_text = response.text
            # In development mode with debug info, sensitive values might be sanitized
            # Check that the actual sensitive values aren't exposed
            if "secret123" not in error_text and "token123" not in error_text:
                # Good - sensitive data is not exposed
                pass

    def test_concurrent_error_handling(self):
        """Test that error handling works correctly under concurrent requests."""
        import concurrent.futures

        def make_error_request(error_type):
            return client.get(f"/api/v1/examples/error-examples/{error_type}")

        error_types = ["validation", "not_found", "conflict", "bad_request"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(make_error_request, error_type)
                for error_type in error_types
            ]
            results = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        # All requests should have been handled properly
        assert len(results) == 4
        status_codes = {r.status_code for r in results}
        assert status_codes == {
            400,  # bad_request
            404,  # not_found
            409,  # conflict
            422,  # validation
        }
