#!/bin/bash
# Setup development environment for platform coordination service

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Setting up development environment for Platform Coordination Service...${NC}"

# Check Python version
echo -e "${YELLOW}Checking Python version...${NC}"
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
REQUIRED_VERSION="3.13"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo -e "${RED}Error: Python $REQUIRED_VERSION or higher is required (found $PYTHON_VERSION)${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python $PYTHON_VERSION${NC}"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv .venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source .venv/bin/activate

# Upgrade pip
echo -e "${YELLOW}Upgrading pip...${NC}"
pip install --upgrade pip setuptools wheel

# Install dependencies
echo -e "${YELLOW}Installing dependencies from requirements.txt...${NC}"
pip install -r requirements.txt

# Verify key packages are installed
echo -e "${YELLOW}Verifying installation...${NC}"
REQUIRED_PACKAGES=(
    "fastapi"
    "uvicorn"
    "sqlalchemy"
    "asyncpg"
    "pytest"
    "httpx"
)

MISSING_PACKAGES=()
for package in "${REQUIRED_PACKAGES[@]}"; do
    if ! pip show "$package" &> /dev/null; then
        MISSING_PACKAGES+=("$package")
    fi
done

if [ ${#MISSING_PACKAGES[@]} -ne 0 ]; then
    echo -e "${RED}Error: The following packages failed to install:${NC}"
    printf '%s\n' "${MISSING_PACKAGES[@]}"
    exit 1
fi

echo -e "${GREEN}✓ All dependencies installed successfully${NC}"

# Check Docker and Docker Compose
echo -e "${YELLOW}Checking Docker setup...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi
echo -e "${GREEN}✓ Docker is installed${NC}"

# Check for docker compose command
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
    echo -e "${GREEN}✓ docker-compose command found${NC}"
elif docker compose version &> /dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
    echo -e "${GREEN}✓ docker compose command found${NC}"
else
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# Setup environment file
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env file from .env.dev...${NC}"
    cp .env.dev .env
    echo -e "${GREEN}✓ .env file created${NC}"
else
    echo -e "${GREEN}✓ .env file already exists${NC}"
fi

# Start PostgreSQL
echo -e "${YELLOW}Starting PostgreSQL container...${NC}"
$DOCKER_COMPOSE -f docker-compose.dev.yml up -d postgres

# Wait for PostgreSQL to be ready
echo -e "${YELLOW}Waiting for PostgreSQL to be ready...${NC}"
for i in {1..30}; do
    if $DOCKER_COMPOSE -f docker-compose.dev.yml exec postgres pg_isready -U coordination_user &> /dev/null; then
        echo -e "${GREEN}✓ PostgreSQL is ready${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}Error: PostgreSQL failed to start${NC}"
        exit 1
    fi
    echo -n "."
    sleep 1
done

# Create test database
echo -e "${YELLOW}Creating test database...${NC}"
$DOCKER_COMPOSE -f docker-compose.dev.yml exec -T postgres psql -U coordination_user -d platform_coordination -c "CREATE DATABASE platform_coordination_test;" 2>/dev/null || true
echo -e "${GREEN}✓ Test database ready${NC}"

echo -e "${GREEN}Development environment setup complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Activate the virtual environment: source .venv/bin/activate"
echo "  2. Run the service: make run"
echo "  3. Run tests: make test"
echo "  4. Run integration tests: make test-integration"
echo ""
echo "PostgreSQL is running at: localhost:5432"
echo "  Database: platform_coordination"
echo "  User: coordination_user"
echo "  Password: coordination_dev_password"