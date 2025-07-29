"""Configuration management for the Platform Coordination Service."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application settings
    app_name: str = "Platform Coordination Service"
    app_version: str = "0.1.0"
    debug: bool = False

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS settings
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8080"]

    # Database settings (for future use)
    database_url: str = "sqlite:///./platform_coordination.db"

    # Service discovery settings
    service_ttl_seconds: int = 60  # How long before a service is considered stale
    service_cleanup_interval_seconds: int = 300  # How often to clean up stale services

    # Logging settings
    log_level: str = "INFO"
    log_format: str = "json"  # "json" or "text"


settings = Settings()
