#!/usr/bin/env python3
"""Measure actual performance of service operations."""

import asyncio
import time
import sys
sys.path.insert(0, 'src')

import httpx
from httpx import ASGITransport
from src.main_db import app
from statistics import mean, stdev

async def measure_registration_time(client, service_num):
    """Measure time to register a single service."""
    data = {
        "name": f"perf-test-service-{service_num}",
        "type": "api",
        "host": "localhost",
        "port": 9000 + service_num,
        "metadata": {
            "version": "1.0.0",
            "environment": "test",
            "tags": {"test": "performance"}
        }
    }
    
    start = time.time()
    response = await client.post("/api/v1/services/register", json=data)
    end = time.time()
    
    return (end - start) * 1000, response.status_code  # Return ms

async def measure_list_time(client):
    """Measure time to list all services."""
    start = time.time()
    response = await client.get("/api/v1/services/")
    end = time.time()
    
    return (end - start) * 1000, response.status_code

async def run_performance_test():
    """Run performance measurements."""
    async with httpx.AsyncClient(
        base_url="http://test",
        transport=ASGITransport(app=app)
    ) as client:
        print("=== Service Registration Performance ===")
        
        # Measure registration times
        reg_times = []
        for i in range(10):
            time_ms, status = await measure_registration_time(client, i)
            if status == 201:
                reg_times.append(time_ms)
                print(f"Registration {i+1}: {time_ms:.2f}ms")
            else:
                print(f"Registration {i+1}: Failed with status {status}")
        
        if reg_times:
            print(f"\nRegistration Stats:")
            print(f"  Average: {mean(reg_times):.2f}ms")
            print(f"  Min: {min(reg_times):.2f}ms")
            print(f"  Max: {max(reg_times):.2f}ms")
            if len(reg_times) > 1:
                print(f"  Std Dev: {stdev(reg_times):.2f}ms")
        
        print("\n=== Service List Performance ===")
        
        # Measure list times
        list_times = []
        for i in range(5):
            time_ms, status = await measure_list_time(client)
            if status == 200:
                list_times.append(time_ms)
                print(f"List {i+1}: {time_ms:.2f}ms")
        
        if list_times:
            print(f"\nList Stats:")
            print(f"  Average: {mean(list_times):.2f}ms")
            print(f"  Min: {min(list_times):.2f}ms")
            print(f"  Max: {max(list_times):.2f}ms")

if __name__ == "__main__":
    asyncio.run(run_performance_test())