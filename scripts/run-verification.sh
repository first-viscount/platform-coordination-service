#!/bin/bash
# Comprehensive service verification script

echo "======================================"
echo "Platform Coordination Service Verification"
echo "======================================"

# Set up environment
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

echo -e "\n1. Running pytest verification tests..."
python -m pytest tests/test_service_verification.py -v --tb=short

echo -e "\n2. Running standalone verification..."
python scripts/verify-service.py

echo -e "\n3. Checking code quality..."
# Run linting if available
if command -v flake8 &> /dev/null; then
    echo "Running flake8..."
    flake8 src/ --count --statistics || true
fi

if command -v mypy &> /dev/null; then
    echo "Running mypy..."
    mypy src/ || true
fi

echo -e "\n======================================"
echo "Verification Complete"
echo "======================================