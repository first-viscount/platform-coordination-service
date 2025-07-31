# Integration Tests - Single Source of Truth

## Prerequisites

1. Python 3.13+ with virtual environment
2. Docker with `docker compose` command
3. Dependencies installed: `pip install -r requirements.txt`

## Running Integration Tests

### Method 1: Using Make (Recommended)
```bash
source .venv/bin/activate
make test-integration
```

### Method 2: Direct Script Execution
```bash
source .venv/bin/activate
./scripts/run-integration-tests.sh
```

### Method 3: Manual pytest
```bash
source .venv/bin/activate
export TEST_DATABASE_URL="postgresql+asyncpg://coordination_user:coordination_dev_password@localhost:5432/platform_coordination_test"
PYTHONPATH=src pytest tests/integration/ -v
```

## What Gets Tested

- Service registration and updates
- Concurrent operations
- Optimistic locking
- Service discovery and filtering
- Health check status updates
- Audit trail functionality
- Performance benchmarks (when run with -s flag)

## Troubleshooting

### ModuleNotFoundError
```bash
pip install -r requirements.txt
```

### Docker Issues
```bash
# Check if PostgreSQL is running
docker compose -f docker-compose.dev.yml ps

# Start PostgreSQL
docker compose -f docker-compose.dev.yml up -d postgres
```

## Test Database

Tests use a separate database: `platform_coordination_test`