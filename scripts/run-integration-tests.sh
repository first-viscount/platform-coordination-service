#!/bin/bash
# Run integration tests for platform coordination service

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to handle errors without exiting the shell
handle_error() {
    echo -e "${RED}✗ Error: $1${NC}"
    return 1
}

echo -e "${YELLOW}Setting up integration test environment...${NC}"

# Try to detect docker compose command
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
else
    echo -e "${RED}Error: Neither 'docker-compose' nor 'docker compose' found!${NC}"
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    return 1 2>/dev/null || exit 1
fi

# Check if PostgreSQL is running
if ! $DOCKER_COMPOSE -f docker-compose.dev.yml ps postgres 2>/dev/null | grep -q "Up\|running"; then
    echo -e "${YELLOW}Starting PostgreSQL...${NC}"
    $DOCKER_COMPOSE -f docker-compose.dev.yml up -d postgres || handle_error "Failed to start PostgreSQL"
    echo "Waiting for PostgreSQL to be ready..."
    sleep 5
fi

# Create test database if it doesn't exist
echo -e "${YELLOW}Creating test database...${NC}"
$DOCKER_COMPOSE -f docker-compose.dev.yml exec -T postgres psql -U coordination_user -d platform_coordination -c "CREATE DATABASE platform_coordination_test;" 2>/dev/null || true

# Set test database URL
export TEST_DATABASE_URL="postgresql+asyncpg://coordination_user:coordination_dev_password@localhost:5432/platform_coordination_test"

# Check if we're being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # Script is being executed directly
    set -e
    
    # Run integration tests
    echo -e "${YELLOW}Running integration tests...${NC}"
    PYTHONPATH=src pytest tests/integration/ -v --tb=short "$@"
    TEST_RESULT=$?
    
    # Check exit code
    if [ $TEST_RESULT -eq 0 ]; then
        echo -e "${GREEN}✓ All integration tests passed!${NC}"
    else
        echo -e "${RED}✗ Integration tests failed!${NC}"
        exit 1
    fi
    
    # Optional: Run performance benchmarks
    if [[ "$*" == *"--benchmark"* ]]; then
        echo -e "${YELLOW}Running performance benchmarks...${NC}"
        PYTHONPATH=src pytest tests/integration/test_performance.py -v -s
    fi
else
    # Script is being sourced - don't use set -e or exit
    echo -e "${YELLOW}Running integration tests (sourced mode)...${NC}"
    
    # Define a function that can be called
    run_integration_tests() {
        PYTHONPATH=src pytest tests/integration/ -v --tb=short "$@"
        local TEST_RESULT=$?
        
        if [ $TEST_RESULT -eq 0 ]; then
            echo -e "${GREEN}✓ All integration tests passed!${NC}"
        else
            echo -e "${RED}✗ Integration tests failed!${NC}"
        fi
        
        # Optional: Run performance benchmarks
        if [[ "$*" == *"--benchmark"* ]]; then
            echo -e "${YELLOW}Running performance benchmarks...${NC}"
            PYTHONPATH=src pytest tests/integration/test_performance.py -v -s
        fi
        
        return $TEST_RESULT
    }
    
    # Run the tests
    run_integration_tests "$@"
fi