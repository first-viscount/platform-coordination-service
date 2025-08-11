#!/usr/bin/env python3
"""Verify Platform Coordination Service without running the server."""

import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from src.main_db import app
from src.core.config import settings


def verify_service():
    """Comprehensive service verification."""
    client = TestClient(app)
    results = {"passed": 0, "failed": 0, "tests": []}
    
    print("🔍 Verifying Platform Coordination Service...\n")
    
    # Test 1: Root endpoint
    print("1. Testing root endpoint...")
    response = client.get("/")
    if response.status_code == 200:
        data = response.json()
        if data.get("service") == settings.app_name and "version" in data:
            print("   ✅ Root endpoint working")
            results["passed"] += 1
        else:
            print("   ❌ Root endpoint response invalid")
            results["failed"] += 1
    else:
        print(f"   ❌ Root endpoint failed: {response.status_code}")
        results["failed"] += 1
    
    # Test 2: Health check
    print("\n2. Testing health check...")
    response = client.get("/health")
    if response.status_code == 200:
        data = response.json()
        if (data.get("status") == "healthy" and 
            data.get("service") == settings.app_name):
            print("   ✅ Health check working")
            results["passed"] += 1
        else:
            print("   ❌ Health check response invalid")
            results["failed"] += 1
    else:
        print(f"   ❌ Health check failed: {response.status_code}")
        results["failed"] += 1
    
    # Test 3: CORS middleware
    print("\n3. Testing CORS middleware...")
    response = client.options("/health", headers={"Origin": "http://localhost:3000"})
    if "access-control-allow-origin" in response.headers:
        print("   ✅ CORS middleware configured")
        results["passed"] += 1
    else:
        print("   ❌ CORS middleware not working")
        results["failed"] += 1
    
    # Test 4: 404 handling
    print("\n4. Testing 404 handling...")
    response = client.get("/nonexistent")
    if response.status_code == 404:
        print("   ✅ 404 handling working")
        results["passed"] += 1
    else:
        print(f"   ❌ 404 handling failed: {response.status_code}")
        results["failed"] += 1
    
    # Summary
    print("\n" + "="*50)
    print(f"📊 SUMMARY: {results['passed']} passed, {results['failed']} failed")
    
    if results["failed"] == 0:
        print("✅ All verification tests passed!")
        print("\n🎉 Platform Coordination Service is ready!")
        print(f"   - Service: {settings.app_name}")
        print(f"   - Version: {settings.app_version}")
        return 0
    else:
        print(f"❌ {results['failed']} tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(verify_service())