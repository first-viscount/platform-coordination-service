"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import health
from src.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Platform Coordination Service API",
)

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

@app.get("/")
async def root():
    """Root endpoint."""
    return {"service": settings.app_name, "version": settings.app_version}
