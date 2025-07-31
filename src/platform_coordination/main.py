"""Main entry point for the Platform Coordination Service."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.platform_coordination.api import health, services
from src.platform_coordination.core.config import settings
from src.platform_coordination.core.logging import setup_logging
from src.api.middleware.error_handling import (
    ErrorHandlingMiddleware,
    create_exception_handlers,
)
from src.api.middleware.logging import LoggingMiddleware
from src.api.routes import example
from src.core.error_utils import create_error_response_examples

# Set up structured logging
logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle."""
    logger.info("Starting Platform Coordination Service", version=settings.app_version)

    # Startup tasks would go here (e.g., database connection)

    yield

    # Shutdown tasks would go here (e.g., close connections)
    logger.info("Shutting down Platform Coordination Service")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Service registry and discovery for the First Viscount platform",
        lifespan=lifespan,
        responses=create_error_response_examples(),  # type: ignore[arg-type]
    )

    # Add error handling middleware FIRST (to catch all errors)
    app.add_middleware(ErrorHandlingMiddleware)

    # Add logging middleware
    app.add_middleware(LoggingMiddleware)

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add custom exception handlers
    create_exception_handlers(app)

    # Include routers
    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(services.router, prefix="/api/v1/services", tags=["services"])
    app.include_router(example.router, tags=["examples"])

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "platform_coordination.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_config=None,  # We're using our own logging config
    )
