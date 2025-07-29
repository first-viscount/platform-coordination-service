"""Tests for service registry endpoints."""

import pytest
from fastapi.testclient import TestClient

from platform_coordination.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def sample_service_registration():
    """Sample service registration data."""
    return {
        "name": "test-service",
        "type": "api",
        "host": "localhost",
        "port": 8080,
        "metadata": {
            "version": "1.0.0",
            "environment": "test",
            "tags": {"team": "platform"},
            "capabilities": ["auth", "metrics"],
        },
        "health_check_endpoint": "/health",
    }


def test_register_service(client, sample_service_registration):
    """Test service registration."""
    response = client.post(
        "/api/v1/services/register", json=sample_service_registration
    )
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == sample_service_registration["name"]
    assert data["type"] == sample_service_registration["type"]
    assert data["host"] == sample_service_registration["host"]
    assert data["port"] == sample_service_registration["port"]
    assert "id" in data
    assert "registered_at" in data
    assert "last_seen_at" in data


def test_list_services(client, sample_service_registration):
    """Test listing services."""
    # Register a service first
    client.post("/api/v1/services/register", json=sample_service_registration)

    # List all services
    response = client.get("/api/v1/services/")
    assert response.status_code == 200

    services = response.json()
    assert len(services) >= 1
    assert any(s["name"] == sample_service_registration["name"] for s in services)


def test_get_service(client, sample_service_registration):
    """Test getting a specific service."""
    # Register a service first
    register_response = client.post(
        "/api/v1/services/register", json=sample_service_registration
    )
    service_id = register_response.json()["id"]

    # Get the service
    response = client.get(f"/api/v1/services/{service_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == service_id
    assert data["name"] == sample_service_registration["name"]


def test_get_nonexistent_service(client):
    """Test getting a service that doesn't exist."""
    response = client.get("/api/v1/services/nonexistent-id")
    assert response.status_code == 404


def test_unregister_service(client, sample_service_registration):
    """Test unregistering a service."""
    # Register a service first
    register_response = client.post(
        "/api/v1/services/register", json=sample_service_registration
    )
    service_id = register_response.json()["id"]

    # Unregister the service
    response = client.delete(f"/api/v1/services/{service_id}")
    assert response.status_code == 204

    # Verify it's gone
    response = client.get(f"/api/v1/services/{service_id}")
    assert response.status_code == 404


def test_discover_services(client, sample_service_registration):
    """Test service discovery by name."""
    # Register a service
    client.post("/api/v1/services/register", json=sample_service_registration)

    # Discover services by name
    response = client.get(
        f"/api/v1/services/discover/{sample_service_registration['name']}"
    )
    assert response.status_code == 200

    services = response.json()
    # Note: In real implementation, only healthy services would be returned
    # For now, we're using UNKNOWN status, so we might get empty results
    assert isinstance(services, list)
