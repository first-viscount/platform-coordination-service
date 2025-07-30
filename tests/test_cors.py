"""Test CORS configuration."""

from fastapi.testclient import TestClient

from src.core.config import settings
from src.main import app

client = TestClient(app)


class TestCORSConfiguration:
    """Test suite for CORS configuration."""

    def test_cors_headers_on_simple_request(self):
        """Test CORS headers on a simple GET request."""
        # Simple request from allowed origin
        response = client.get("/health", headers={"Origin": "http://localhost:3000"})

        assert response.status_code == 200
        assert (
            response.headers["access-control-allow-origin"] == "http://localhost:3000"
        )
        assert response.headers["access-control-allow-credentials"] == "true"

    def test_cors_preflight_request(self):
        """Test CORS preflight (OPTIONS) request."""
        response = client.options(
            "/api/v1/examples/items",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

        assert response.status_code == 200
        assert (
            response.headers["access-control-allow-origin"] == "http://localhost:3000"
        )
        assert response.headers["access-control-allow-credentials"] == "true"
        assert "POST" in response.headers["access-control-allow-methods"]
        assert (
            "content-type" in response.headers["access-control-allow-headers"].lower()
        )

    def test_cors_with_disallowed_origin(self):
        """Test CORS with origin not in allowed list."""
        response = client.get("/health", headers={"Origin": "http://evil.com"})

        # The request should still succeed
        assert response.status_code == 200

        # But CORS headers should not allow the origin
        # FastAPI's CORS middleware won't add the header if origin is not allowed
        assert response.headers.get("access-control-allow-origin") != "http://evil.com"

    def test_cors_allows_all_methods(self):
        """Test that CORS allows all HTTP methods as configured."""
        response = client.options(
            "/api/v1/examples/items",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "DELETE",
            },
        )

        assert response.status_code == 200
        allowed_methods = response.headers.get("access-control-allow-methods", "")

        # Should allow all common methods
        for method in ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]:
            assert method in allowed_methods or "*" in allowed_methods

    def test_cors_allows_all_headers(self):
        """Test that CORS allows all headers as configured."""
        custom_headers = [
            "x-custom-header",
            "authorization",
            "content-type",
            "x-api-key",
        ]

        for header in custom_headers:
            response = client.options(
                "/api/v1/examples/items",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": header,
                },
            )

            assert response.status_code == 200
            allowed_headers = response.headers.get(
                "access-control-allow-headers", ""
            ).lower()
            assert header in allowed_headers or "*" in allowed_headers

    def test_cors_on_error_responses(self):
        """Test that CORS headers are included on error responses."""
        # Test 404 error
        response = client.get(
            "/api/v1/examples/items/non-existent",
            headers={"Origin": "http://localhost:3000"},
        )

        assert response.status_code == 404
        assert (
            response.headers["access-control-allow-origin"] == "http://localhost:3000"
        )

        # Test 422 validation error
        response = client.post(
            "/api/v1/examples/items",
            json={"invalid": "data"},
            headers={"Origin": "http://localhost:3000"},
        )

        assert response.status_code == 422
        assert (
            response.headers["access-control-allow-origin"] == "http://localhost:3000"
        )

        # Test 500 internal error
        response = client.get(
            "/api/v1/examples/divide/1/0", headers={"Origin": "http://localhost:3000"}
        )

        assert response.status_code == 500
        assert (
            response.headers["access-control-allow-origin"] == "http://localhost:3000"
        )

    def test_cors_credentials_flag(self):
        """Test that credentials flag is properly set."""
        response = client.get("/health", headers={"Origin": "http://localhost:3000"})

        # allow_credentials is set to True in our configuration
        assert response.headers["access-control-allow-credentials"] == "true"

    def test_cors_vary_header(self):
        """Test that Vary header includes Origin."""
        response = client.get("/health", headers={"Origin": "http://localhost:3000"})

        vary_header = response.headers.get("vary", "")
        # The Vary header should include Origin for proper caching
        assert "origin" in vary_header.lower()

    def test_cors_on_all_endpoints(self):
        """Test that CORS is applied to all endpoints."""
        endpoints = [
            "/",
            "/health",
            "/api/v1/examples/items",
            "/docs",  # Even documentation endpoints
            "/openapi.json",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint, headers={"Origin": "http://localhost:3000"})

            # All endpoints should have CORS headers when accessed from allowed origin
            if response.status_code == 200:
                assert "access-control-allow-origin" in response.headers

    def test_cors_preflight_max_age(self):
        """Test CORS preflight cache duration."""
        response = client.options(
            "/api/v1/examples/items",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )

        # Check if max-age header is set (browser can cache preflight)
        if "access-control-max-age" in response.headers:
            max_age = int(response.headers["access-control-max-age"])
            assert max_age > 0  # Should have some caching

    def test_multiple_origins_configuration(self):
        """Test behavior with multiple configured origins."""
        # Our settings only have localhost:3000, but let's verify the behavior
        test_origins = [
            "http://localhost:3000",  # Configured
            "http://localhost:3001",  # Not configured
            "https://localhost:3000",  # Different protocol
        ]

        for origin in test_origins:
            response = client.get("/health", headers={"Origin": origin})

            assert response.status_code == 200

            # Only the configured origin should get CORS headers
            if origin in settings.cors_origins:
                assert response.headers.get("access-control-allow-origin") == origin
            else:
                # Non-allowed origins might not get the header or get a different response
                assert response.headers.get("access-control-allow-origin") != origin
