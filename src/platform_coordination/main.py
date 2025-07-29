"""Main entry point for the Platform Coordination Service."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from platform_coordination.api import health, services
from platform_coordination.core.config import settings
from platform_coordination.core.logging import setup_logging

# Set up structured logging
logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
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
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(services.router, prefix="/api/v1/services", tags=["services"])

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
