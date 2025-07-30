"""Main FastAPI application with database support."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from src.api.middleware.error_handling import (
    ErrorHandlingMiddleware,
    create_exception_handlers,
)
from src.api.routes import example, health
from src.core.config import settings
from src.core.database import close_db, init_db
from src.core.logging import get_logger, setup_logging
from src.core.middleware import LoggingMiddleware
from src.platform_coordination.api import services_db

# Setup logging
setup_logging(
    level=settings.log_level,
    service_name=settings.app_name,
    environment=settings.environment,
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan management."""
    # Startup
    logger.info("Starting Platform Coordination Service", version=settings.app_version)

    # Initialize database
    if settings.database_url:
        try:
            await init_db()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize database", error=str(e))
            # In production, you might want to fail fast here

    yield

    # Shutdown
    logger.info("Shutting down Platform Coordination Service")
    if settings.database_url:
        await close_db()


# Custom OpenAPI schema
def custom_openapi() -> dict[str, Any]:
    """Generate custom OpenAPI schema with enhanced documentation."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=settings.app_name,
        version=settings.app_version,
        description="""
## Platform Coordination Service API

The Platform Coordination Service provides a centralized API for managing and coordinating various platform services.

### Key Features:
- **Service Registry**: Register and discover platform services
- **Health Monitoring**: Real-time health checks for service availability
- **Service Coordination**: Manage interactions between platform services
- **Error Handling**: Comprehensive error responses with detailed context
- **API Versioning**: Stable API with version support

### Service Registry
The service registry allows microservices to:
- Register themselves with the platform
- Discover other services by name or type
- Update their health status
- Query for healthy service instances

### API Versioning
This API follows semantic versioning. The current version is v1.
- Version is included in the URL path: `/api/v1/...`
- Breaking changes will result in a new major version

### Authentication
Currently, the API is open for development. Authentication will be added in future versions.

### Error Responses
All error responses follow a consistent format:
```json
{
  "error": {
    "type": "ValidationError",
    "message": "Validation failed",
    "code": "VALIDATION_ERROR",
    "details": [...],
    "timestamp": "2025-01-29T12:00:00Z",
    "path": "/api/v1/examples/items"
  }
}
```

### Rate Limiting
No rate limiting is currently implemented. This will be added in future versions.
        """,
        routes=app.routes,
        servers=[
            {"url": "http://localhost:8000", "description": "Local development server"},
            {
                "url": "http://platform-coordination-service:8000",
                "description": "Docker service",
            },
        ],
    )

    # Add custom error response examples
    openapi_schema["components"]["schemas"]["ErrorResponse"] = {
        "type": "object",
        "properties": {
            "error": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "example": "ValidationError"},
                    "message": {"type": "string", "example": "Validation failed"},
                    "code": {"type": "string", "example": "VALIDATION_ERROR"},
                    "details": {
                        "type": "array",
                        "items": {"type": "object"},
                        "example": [
                            {"field": "email", "message": "Invalid email format"}
                        ],
                    },
                    "timestamp": {"type": "string", "format": "date-time"},
                    "path": {"type": "string", "example": "/api/v1/examples/items"},
                    "request_id": {
                        "type": "string",
                        "example": "550e8400-e29b-41d4-a716-446655440000",
                    },
                },
            }
        },
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Platform Coordination Service API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.openapi = custom_openapi  # type: ignore[method-assign]

# Add middleware (order matters - error handling should be outermost)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(LoggingMiddleware)

# Create custom exception handlers
create_exception_handlers(app)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(example.router, prefix="/api/v1", tags=["examples"])
app.include_router(
    services_db.router,
    prefix="/api/v1/services",
    tags=["service-registry"],
)


@app.get(
    "/",
    summary="Service Information",
    description="""
Get basic information about the Platform Coordination Service.

This is the root endpoint that provides:
- Service name
- Current version
- Database status (if connected)

Useful for quick service identification and version checking.
    """,
    response_description="Service information",
    responses={
        200: {
            "description": "Service information",
            "content": {
                "application/json": {
                    "example": {
                        "service": "platform-coordination-service",
                        "version": "0.1.0",
                        "database": "connected",
                    }
                }
            },
        }
    },
    tags=["service-info"],
)
async def root() -> dict[str, str]:
    """Root endpoint."""
    info = {
        "service": settings.app_name,
        "version": settings.app_version,
    }

    # Add database status if configured
    if settings.database_url:
        info["database"] = "connected"
    else:
        info["database"] = "not configured"

    return info
