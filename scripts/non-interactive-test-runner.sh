#!/bin/bash
# Non-interactive integration test runner
# This script runs without any user prompts

set -e
cd "$(dirname "$0")/.."

echo "=== Non-Interactive Integration Test Runner ==="
echo "Starting at: $(date)"

# Check Python and venv
if [ ! -d ".venv" ]; then
    echo "ERROR: .venv not found. Creating would require user interaction."
    echo "Please run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Create results directory
mkdir -p test-results

# Export required environment variables
export TEST_DATABASE_URL="postgresql+asyncpg://coordination_user:coordination_dev_password@localhost:5432/platform_coordination_test"
export PYTHONPATH=src

# Check if PostgreSQL is accessible (no docker commands that might prompt)
echo "Checking PostgreSQL connectivity..."
python3 -c "
import asyncio
import asyncpg
async def check():
    try:
        conn = await asyncpg.connect('$TEST_DATABASE_URL')
        await conn.close()
        print('✓ PostgreSQL connection successful')
        return True
    except Exception as e:
        print(f'✗ PostgreSQL connection failed: {e}')
        return False
asyncio.run(check())
" || echo "Warning: Database connection check failed"

# Run integration tests and capture output
echo "Running integration tests..."
source .venv/bin/activate 2>/dev/null || true
python -m pytest tests/integration/ -v --tb=short --no-header 2>&1 | tee test-results/integration.log | grep -E "PASSED|FAILED|ERROR" || true

# Extract summary
echo ""
echo "=== Test Summary ==="
grep -E "passed|failed|errors" test-results/integration.log | tail -1 || echo "No summary found"

# Run performance tests separately
echo ""
echo "Running performance benchmarks..."
python -m pytest tests/integration/test_performance.py -v -s --no-header 2>&1 | tee test-results/performance.log | grep -E "Performance:|Throughput:|ms" || true

echo ""
echo "Completed at: $(date)"
echo "Full results saved to test-results/"