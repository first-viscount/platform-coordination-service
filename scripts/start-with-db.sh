#!/bin/bash
# Start the platform coordination service with database support

set -e

# Load environment variables from .env.dev
if [ -f .env.dev ]; then
    export $(grep -v '^#' .env.dev | xargs)
fi

# Check if PostgreSQL is running
echo "Checking PostgreSQL connection..."
docker-compose -f docker-compose.dev.yml ps postgres | grep -q "Up" || {
    echo "PostgreSQL is not running. Starting it now..."
    docker-compose -f docker-compose.dev.yml up -d postgres
    echo "Waiting for PostgreSQL to be ready..."
    sleep 5
}

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Run the application with database support
echo "Starting application with database support..."
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
uvicorn src.main_db:app --reload --host 0.0.0.0 --port 8000