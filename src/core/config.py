"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )

    app_name: str = "platform-coordination-service"
    app_version: str = "0.1.0"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Logging configuration
    log_level: str = "INFO"
    log_format: str = "json"  # "json" or "console"
    log_request_body: bool = (
        False  # Whether to log request bodies (be careful with sensitive data)
    )
    log_response_body: bool = False  # Whether to log response bodies

    # Environment
    environment: str = "development"  # development, staging, production

    # Database
    database_url: str | None = None
    db_pool_size: int = 10
    db_pool_max_overflow: int = 20
    db_pool_timeout: int = 30


settings = Settings()
