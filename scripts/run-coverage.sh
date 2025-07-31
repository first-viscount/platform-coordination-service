#!/bin/bash
set -e
cd "$(dirname "$0")/.."

echo "=== Running Tests with Coverage ==="
echo "Starting at: $(date)"

# Activate virtual environment
source .venv/bin/activate

# Set environment variables
export PYTHONPATH=src
export TEST_DATABASE_URL="postgresql+asyncpg://coordination_user:coordination_dev_password@localhost:5432/platform_coordination_test"

# Create coverage directory
mkdir -p test-results/coverage

# Run tests with coverage
echo "Running integration tests with coverage..."
python -m pytest tests/integration/ \
    --cov=src \
    --cov-report=html:test-results/coverage/html \
    --cov-report=term-missing \
    --cov-report=json:test-results/coverage/coverage.json \
    -v

echo ""
echo "Coverage report saved to test-results/coverage/"
echo "HTML report: test-results/coverage/html/index.html"
echo "Completed at: $(date)"