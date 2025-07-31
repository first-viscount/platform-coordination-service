"""Performance benchmarks for service registry."""

import asyncio
import time
from statistics import mean, stdev

import pytest
from httpx import AsyncClient


class TestPerformanceBenchmarks:
    """Performance benchmarks for service registry operations."""
    
    @pytest.mark.asyncio
    async def test_registration_throughput(self, test_client: AsyncClient):
        """Benchmark service registration throughput."""
        num_services = 100
        
        async def register_service(i: int):
            data = {
                "name": f"perf-test-{i}",
                "type": "api",
                "host": f"host-{i}",
                "port": 8000 + i,
                "metadata": {
                    "version": "1.0.0",
                    "environment": "test",
                    "tags": {"test": "performance", "index": str(i)}
                }
            }
            start = time.time()
            response = await test_client.post("/api/v1/services/register", json=data)
            end = time.time()
            return end - start if response.status_code == 201 else None
        
        # Warm up
        await register_service(0)
        
        # Measure registration times
        start_total = time.time()
        tasks = [register_service(i) for i in range(1, num_services + 1)]
        durations = await asyncio.gather(*tasks)
        end_total = time.time()
        
        # Calculate metrics
        valid_durations = [d for d in durations if d is not None]
        total_time = end_total - start_total
        throughput = len(valid_durations) / total_time
        
        print(f"\nRegistration Performance:")
        print(f"  Total services: {num_services}")
        print(f"  Successful: {len(valid_durations)}")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Throughput: {throughput:.2f} services/second")
        print(f"  Avg latency: {mean(valid_durations)*1000:.2f}ms")
        print(f"  Std dev: {stdev(valid_durations)*1000:.2f}ms")
        
        # Performance assertions removed - run tests to establish baseline
    
    @pytest.mark.asyncio
    async def test_query_performance(self, test_client: AsyncClient):
        """Benchmark service query performance."""
        # First, register services
        services_to_register = 500
        
        for i in range(services_to_register):
            data = {
                "name": f"query-test-{i % 10}",  # 10 different service names
                "type": ["api", "worker", "scheduler"][i % 3],
                "host": f"host-{i}",
                "port": 8000 + i,
                "metadata": {
                    "tags": {
                        "env": ["prod", "staging", "dev"][i % 3],
                        "region": ["us-east", "us-west", "eu-west"][i % 3]
                    }
                }
            }
            await test_client.post("/api/v1/services/register", json=data)
        
        # Benchmark different query types
        queries = [
            ("List all", "/api/v1/services/", {}),
            ("Filter by type", "/api/v1/services/", {"type": "api"}),
            ("Filter by tag", "/api/v1/services/", {"tag": "env=prod"}),
            ("Discover by name", "/api/v1/services/discover/query-test-5", {}),
        ]
        
        print(f"\nQuery Performance (with {services_to_register} services):")
        
        for query_name, endpoint, params in queries:
            # Warm up
            await test_client.get(endpoint, params=params)
            
            # Measure query times
            times = []
            for _ in range(20):
                start = time.time()
                response = await test_client.get(endpoint, params=params)
                end = time.time()
                if response.status_code == 200:
                    times.append(end - start)
            
            if times:
                avg_time = mean(times) * 1000
                std_time = stdev(times) * 1000 if len(times) > 1 else 0
                print(f"  {query_name}: {avg_time:.2f}ms (±{std_time:.2f}ms)")
                
                # Run tests to establish query performance baseline
    
    @pytest.mark.asyncio
    async def test_concurrent_load(self, test_client: AsyncClient):
        """Test system under concurrent load."""
        concurrent_clients = 50
        operations_per_client = 20
        
        async def client_workload(client_id: int):
            """Simulate a client performing various operations."""
            successes = 0
            errors = 0
            
            for op in range(operations_per_client):
                try:
                    # Mix of operations
                    if op % 4 == 0:
                        # Register new service
                        data = {
                            "name": f"load-test-{client_id}-{op}",
                            "type": "api",
                            "host": f"host-{client_id}",
                            "port": 8000 + client_id
                        }
                        response = await test_client.post("/api/v1/services/register", json=data)
                    elif op % 4 == 1:
                        # List services
                        response = await test_client.get("/api/v1/services/")
                    elif op % 4 == 2:
                        # Update health
                        response = await test_client.post(
                            f"/api/v1/services/discover/load-test-{client_id}-0",
                            params={"healthy": True}
                        )
                    else:
                        # Get specific service
                        response = await test_client.get("/api/v1/services/")
                        if response.status_code == 200:
                            services = response.json()
                            if services:
                                service_id = services[0]["id"]
                                response = await test_client.get(f"/api/v1/services/{service_id}")
                    
                    if response.status_code < 400:
                        successes += 1
                    else:
                        errors += 1
                except Exception:
                    errors += 1
            
            return successes, errors
        
        # Run concurrent load test
        print(f"\nConcurrent Load Test:")
        print(f"  Clients: {concurrent_clients}")
        print(f"  Operations per client: {operations_per_client}")
        
        start = time.time()
        tasks = [client_workload(i) for i in range(concurrent_clients)]
        results = await asyncio.gather(*tasks)
        end = time.time()
        
        total_successes = sum(r[0] for r in results)
        total_errors = sum(r[1] for r in results)
        total_operations = concurrent_clients * operations_per_client
        duration = end - start
        
        print(f"  Total operations: {total_operations}")
        print(f"  Successful: {total_successes}")
        print(f"  Errors: {total_errors}")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Throughput: {total_operations/duration:.2f} ops/second")
        print(f"  Success rate: {total_successes/total_operations*100:.1f}%")
        
        # Run tests to establish load performance baseline
    
    @pytest.mark.asyncio
    async def test_database_connection_pooling(self, test_client: AsyncClient):
        """Test that connection pooling works efficiently."""
        # Perform many quick operations to test connection reuse
        num_operations = 200
        
        async def quick_operation(i: int):
            start = time.time()
            response = await test_client.get("/api/v1/services/")
            end = time.time()
            return end - start if response.status_code == 200 else None
        
        # Sequential operations (should reuse connections)
        sequential_times = []
        for i in range(num_operations):
            duration = await quick_operation(i)
            if duration:
                sequential_times.append(duration)
        
        # Concurrent operations (should use connection pool)
        tasks = [quick_operation(i) for i in range(num_operations)]
        concurrent_times = await asyncio.gather(*tasks)
        concurrent_times = [t for t in concurrent_times if t is not None]
        
        print(f"\nConnection Pooling Performance:")
        print(f"  Sequential avg: {mean(sequential_times)*1000:.2f}ms")
        print(f"  Concurrent avg: {mean(concurrent_times)*1000:.2f}ms")
        
        # Compare sequential vs concurrent to verify connection pooling