"""Application configuration."""

from typing import List
from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
    )
    
    app_name: str = "platform-coordination-service"
    app_version: str = "0.1.0"
    
    # CORS
    cors_origins: List[str] = ["http://localhost:3000"]
    
    # Logging configuration
    log_level: str = "INFO"
    log_format: str = "json"  # "json" or "console"
    log_request_body: bool = False  # Whether to log request bodies (be careful with sensitive data)
    log_response_body: bool = False  # Whether to log response bodies
    
    # Environment
    environment: str = "development"  # development, staging, production


settings = Settings()
