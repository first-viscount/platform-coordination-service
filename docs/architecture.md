# Platform Coordination Service Architecture

## Overview

The Platform Coordination Service is a FastAPI-based service registry and discovery system for the First Viscount platform. It provides a centralized location for services to register themselves and discover other services.

## Project Structure

```
platform-coordination-service/
├── src/
│   └── platform_coordination/
│       ├── __init__.py           # Package initialization
│       ├── main.py               # FastAPI app entry point
│       ├── api/                  # API endpoints
│       │   ├── __init__.py
│       │   ├── health.py         # Health check endpoints
│       │   └── services.py       # Service registry endpoints
│       ├── core/                 # Core functionality
│       │   ├── __init__.py
│       │   ├── config.py         # Configuration management
│       │   └── logging.py        # Structured logging setup
│       └── models/               # Data models
│           ├── __init__.py
│           └── service.py        # Service registration models
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── test_health.py           # Health endpoint tests
│   └── test_services.py         # Service registry tests
├── .env.example                  # Environment variables template
├── .gitignore                    # Git ignore rules
├── .ruff.toml                    # Ruff linter configuration
├── docker-compose.yml            # Docker compose for local dev
├── Dockerfile                    # Container definition
├── LICENSE                       # MIT License
├── Makefile                      # Development commands
├── mypy.ini                      # Type checking configuration
├── pyproject.toml                # Python project metadata
├── README.md                     # Project documentation
└── requirements.txt              # Python dependencies
```

## Key Design Decisions

### 1. **Modular Architecture**
- Clear separation of concerns with dedicated modules for API, core functionality, and models
- Each module has a single responsibility
- Easy to extend with new endpoints or functionality

### 2. **Configuration Management**
- Uses Pydantic Settings for type-safe configuration
- Environment variables for deployment flexibility
- Sensible defaults for development

### 3. **Structured Logging**
- Structlog for JSON-formatted logs in production
- Human-readable logs for development
- Contextual logging throughout the application

### 4. **API Design**
- RESTful endpoints following standard conventions
- Consistent response formats
- Proper HTTP status codes
- Input validation using Pydantic models

### 5. **Testing Strategy**
- Comprehensive test coverage from day one
- FastAPI TestClient for integration tests
- Fixtures for reusable test data

## Core Components

### Service Registry (`/api/v1/services`)
- **POST /register** - Register a new service or update existing
- **GET /** - List all services with optional filters
- **GET /{service_id}** - Get specific service details
- **DELETE /{service_id}** - Unregister a service
- **GET /discover/{service_name}** - Discover healthy services by name

### Health Checks (`/health`)
- **GET /** - Basic health check
- **GET /ready** - Readiness probe (for k8s)
- **GET /live** - Liveness probe (for k8s)

### Models
- **ServiceRegistration** - Input model for registering services
- **ServiceInfo** - Complete service information with metadata
- **ServiceStatus** - Enum for service health states
- **ServiceType** - Enum for different service types

## Development Workflow

```bash
# Install dependencies
make install

# Run linting and formatting
make format
make lint

# Run tests
make test

# Run type checking
make type-check

# Run the service locally
make run

# Run all checks
make check
```

## Future Enhancements

1. **Persistence Layer**
   - SQLAlchemy models for database storage
   - Alembic for migrations
   - Repository pattern for data access

2. **Health Monitoring**
   - Background task to periodically check service health
   - Automatic status updates based on health checks
   - Circuit breaker pattern for failed services

3. **Service Mesh Integration**
   - Istio/Linkerd compatibility
   - mTLS support
   - Distributed tracing

4. **Metrics & Observability**
   - Prometheus metrics endpoint
   - OpenTelemetry integration
   - Performance monitoring

5. **Advanced Features**
   - Service versioning
   - Blue-green deployments support
   - Load balancing hints
   - Service dependencies tracking