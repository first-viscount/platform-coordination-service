"""Integration tests for service registry with PostgreSQL."""

import asyncio
from uuid import UUID

import pytest
from httpx import AsyncClient


class TestServiceRegistration:
    """Test service registration functionality."""

    @pytest.mark.asyncio
    async def test_register_new_service(
        self, test_client: AsyncClient, sample_service_data
    ):
        """Test registering a new service."""
        response = await test_client.post(
            "/api/v1/services/register", json=sample_service_data
        )

        assert response.status_code == 201
        data = response.json()

        assert data["name"] == sample_service_data["name"]
        assert data["type"] == sample_service_data["type"]
        assert data["host"] == sample_service_data["host"]
        assert data["port"] == sample_service_data["port"]
        assert data["status"] == "unknown"
        assert "id" in data
        assert UUID(data["id"])  # Validate UUID format
        assert data["metadata"]["tags"] == sample_service_data["metadata"]["tags"]

    @pytest.mark.asyncio
    async def test_register_duplicate_service(
        self, test_client: AsyncClient, sample_service_data
    ):
        """Test that re-registering the same service updates it."""
        # Register first time
        response1 = await test_client.post(
            "/api/v1/services/register", json=sample_service_data
        )
        assert response1.status_code == 201
        service1 = response1.json()

        # Register again with updated metadata
        updated_data = sample_service_data.copy()
        updated_data["metadata"]["version"] = "2.0.0"

        response2 = await test_client.post(
            "/api/v1/services/register", json=updated_data
        )
        assert response2.status_code == 201
        service2 = response2.json()

        # Should have same ID but updated metadata
        assert service2["id"] == service1["id"]
        assert service2["metadata"]["version"] == "2.0.0"
        assert service2["registered_at"] == service1["registered_at"]
        assert service2["last_seen_at"] > service1["last_seen_at"]


class TestConcurrentOperations:
    """Test thread safety with concurrent operations."""

    @pytest.mark.asyncio
    async def test_concurrent_registrations(self, test_client: AsyncClient):
        """Test multiple services registering concurrently."""

        async def register_service(name: str, port: int):
            data = {
                "name": f"concurrent-{name}",
                "type": "api",
                "host": "localhost",
                "port": port,
                "metadata": {
                    "version": "1.0.0",
                    "environment": "test",
                    "tags": {"instance": name},
                },
            }
            response = await test_client.post("/api/v1/services/register", json=data)
            return response

        # Register 10 services concurrently
        tasks = [register_service(f"service-{i}", 8000 + i) for i in range(10)]
        responses = await asyncio.gather(*tasks)

        # All should succeed
        assert all(r.status_code == 201 for r in responses)

        # Verify all services were created
        list_response = await test_client.get("/api/v1/services/")
        services = list_response.json()
        concurrent_services = [
            s for s in services if s["name"].startswith("concurrent-")
        ]
        assert len(concurrent_services) == 10

    @pytest.mark.asyncio
    async def test_concurrent_updates_same_service(
        self, test_client: AsyncClient, sample_service_data
    ):
        """Test concurrent updates to the same service."""
        # Register initial service
        response = await test_client.post(
            "/api/v1/services/register", json=sample_service_data
        )
        service = response.json()
        service_id = service["id"]

        async def update_health(healthy: bool):
            response = await test_client.post(
                f"/api/v1/services/{service_id}/health", params={"healthy": healthy}
            )
            return response

        # Simulate 20 concurrent health updates
        tasks = [update_health(i % 2 == 0) for i in range(20)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # All updates should succeed (no exceptions)
        assert all(not isinstance(r, Exception) for r in responses)
        assert all(
            r.status_code == 200 for r in responses if not isinstance(r, Exception)
        )


class TestOptimisticLocking:
    """Test optimistic locking prevents lost updates."""

    @pytest.mark.asyncio
    async def test_version_increment_on_update(
        self, test_client: AsyncClient, db_session, sample_service_data
    ):
        """Test that version increments on each update."""
        from src.repositories.service import ServiceRepository

        # Register service
        response = await test_client.post(
            "/api/v1/services/register", json=sample_service_data
        )
        service_data = response.json()
        service_id = UUID(service_data["id"])

        # Get initial version directly from DB
        repo = ServiceRepository(db_session)
        service = await repo.get(service_id)
        initial_version = service.version

        # Update service health
        await test_client.post(
            f"/api/v1/services/{service_id}/health", params={"healthy": True}
        )

        # Check version incremented
        await db_session.refresh(service)
        assert service.version == initial_version + 1

        # Another update
        await test_client.post(
            f"/api/v1/services/{service_id}/health", params={"healthy": False}
        )

        # Version should increment again
        await db_session.refresh(service)
        assert service.version == initial_version + 2


class TestServiceDiscovery:
    """Test service discovery and filtering."""

    @pytest.mark.asyncio
    async def test_list_all_services(
        self, test_client: AsyncClient, multiple_services_data
    ):
        """Test listing all registered services."""
        # Register multiple services
        for service_data in multiple_services_data:
            await test_client.post("/api/v1/services/register", json=service_data)

        # List all services
        response = await test_client.get("/api/v1/services/")
        assert response.status_code == 200

        services = response.json()
        assert len(services) == len(multiple_services_data)

        # Verify all services are present
        service_names = {s["name"] for s in services}
        expected_names = {s["name"] for s in multiple_services_data}
        assert service_names == expected_names

    @pytest.mark.asyncio
    async def test_filter_by_type(
        self, test_client: AsyncClient, multiple_services_data
    ):
        """Test filtering services by type."""
        # Register services
        for service_data in multiple_services_data:
            await test_client.post("/api/v1/services/register", json=service_data)

        # Filter by type
        response = await test_client.get("/api/v1/services/", params={"type": "api"})
        services = response.json()

        assert len(services) == 1
        assert all(s["type"] == "api" for s in services)

    @pytest.mark.asyncio
    async def test_filter_by_tag(
        self, test_client: AsyncClient, multiple_services_data
    ):
        """Test filtering services by tag."""
        # Register services
        for service_data in multiple_services_data:
            await test_client.post("/api/v1/services/register", json=service_data)

        # Filter by tag
        response = await test_client.get(
            "/api/v1/services/", params={"tag": "env=prod"}
        )
        services = response.json()

        assert len(services) == 3  # Three prod services
        assert all(s["metadata"]["tags"]["env"] == "prod" for s in services)

    @pytest.mark.asyncio
    async def test_discover_by_name(
        self, test_client: AsyncClient, sample_service_data
    ):
        """Test discovering services by name."""
        # Register service
        await test_client.post("/api/v1/services/register", json=sample_service_data)

        # Update health to make it healthy
        services = (await test_client.get("/api/v1/services/")).json()
        service_id = services[0]["id"]
        await test_client.post(
            f"/api/v1/services/{service_id}/health", params={"healthy": True}
        )

        # Discover by name
        response = await test_client.get(
            f"/api/v1/services/discover/{sample_service_data['name']}"
        )
        discovered = response.json()

        assert len(discovered) == 1
        assert discovered[0]["name"] == sample_service_data["name"]
        assert discovered[0]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_discover_excludes_unhealthy(self, test_client: AsyncClient):
        """Test that discovery excludes unhealthy services by default."""
        # Register two instances of same service
        service_data = {
            "name": "multi-instance",
            "type": "api",
            "host": "host1",
            "port": 8080,
            "metadata": {
                "version": "1.0.0",
                "environment": "test",
                "tags": {"test": "health"},
            },
        }

        # Register first instance
        response1 = await test_client.post(
            "/api/v1/services/register", json=service_data
        )
        service1_id = response1.json()["id"]

        # Register second instance
        service_data["host"] = "host2"
        response2 = await test_client.post(
            "/api/v1/services/register", json=service_data
        )
        service2_id = response2.json()["id"]

        # Make first healthy, second unhealthy
        await test_client.post(
            f"/api/v1/services/{service1_id}/health", params={"healthy": True}
        )
        await test_client.post(
            f"/api/v1/services/{service2_id}/health", params={"healthy": False}
        )

        # Discover should only return healthy instance
        response = await test_client.get("/api/v1/services/discover/multi-instance")
        discovered = response.json()

        assert len(discovered) == 1
        assert discovered[0]["id"] == service1_id
        assert discovered[0]["status"] == "healthy"


class TestHealthChecks:
    """Test health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_updates_status(
        self, test_client: AsyncClient, sample_service_data
    ):
        """Test that health checks update service status."""
        # Register service
        response = await test_client.post(
            "/api/v1/services/register", json=sample_service_data
        )
        service = response.json()
        service_id = service["id"]

        # Initial status should be unknown
        assert service["status"] == "unknown"

        # Update health - healthy
        response = await test_client.post(
            f"/api/v1/services/{service_id}/health", params={"healthy": True}
        )
        assert response.status_code == 200
        updated = response.json()
        assert updated["status"] == "healthy"
        assert updated["health_check_failures"] == 0

        # Update health - unhealthy
        response = await test_client.post(
            f"/api/v1/services/{service_id}/health", params={"healthy": False}
        )
        updated = response.json()
        assert updated["status"] == "degraded"  # First failure = degraded
        assert updated["health_check_failures"] == 1

        # More failures
        await test_client.post(
            f"/api/v1/services/{service_id}/health", params={"healthy": False}
        )
        response = await test_client.post(
            f"/api/v1/services/{service_id}/health", params={"healthy": False}
        )
        updated = response.json()
        assert updated["status"] == "unhealthy"  # 3 failures = unhealthy
        assert updated["health_check_failures"] == 3

        # Recover
        response = await test_client.post(
            f"/api/v1/services/{service_id}/health", params={"healthy": True}
        )
        updated = response.json()
        assert updated["status"] == "healthy"
        assert updated["health_check_failures"] == 0


class TestServiceDeletion:
    """Test service unregistration."""

    @pytest.mark.asyncio
    async def test_delete_service(self, test_client: AsyncClient, sample_service_data):
        """Test deleting a service."""
        # Register service
        response = await test_client.post(
            "/api/v1/services/register", json=sample_service_data
        )
        service = response.json()
        service_id = service["id"]

        # Delete service
        response = await test_client.delete(f"/api/v1/services/{service_id}")
        assert response.status_code == 204

        # Verify it's gone
        response = await test_client.get(f"/api/v1/services/{service_id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent_service(self, test_client: AsyncClient):
        """Test deleting a service that doesn't exist."""
        fake_id = "550e8400-e29b-41d4-a716-446655440000"
        response = await test_client.delete(f"/api/v1/services/{fake_id}")
        assert response.status_code == 404


class TestAuditTrail:
    """Test audit trail functionality."""

    @pytest.mark.asyncio
    async def test_service_events_logged(
        self, test_client: AsyncClient, db_session, sample_service_data
    ):
        """Test that service events are logged in the audit trail."""
        from sqlalchemy import select

        from src.models.service import ServiceEvent

        # Register service
        response = await test_client.post(
            "/api/v1/services/register", json=sample_service_data
        )
        service = response.json()
        service_id = UUID(service["id"])

        # Check registration event
        stmt = select(ServiceEvent).where(ServiceEvent.service_id == service_id)
        result = await db_session.execute(stmt)
        events = result.scalars().all()

        assert len(events) == 1
        assert events[0].event_type == "service_registered"
        assert events[0].event_data["service_name"] == sample_service_data["name"]

        # Update health
        await test_client.post(
            f"/api/v1/services/{service_id}/health", params={"healthy": True}
        )

        # Check status change event
        result = await db_session.execute(stmt)
        events = result.scalars().all()

        assert len(events) == 2
        status_event = next(e for e in events if e.event_type == "status_change")
        assert status_event.event_data["old_status"] == "unknown"
        assert status_event.event_data["new_status"] == "healthy"

        # Delete service
        await test_client.delete(f"/api/v1/services/{service_id}")

        # Events should be cascade deleted
        result = await db_session.execute(stmt)
        events = result.scalars().all()
        assert len(events) == 0  # All events deleted with service
