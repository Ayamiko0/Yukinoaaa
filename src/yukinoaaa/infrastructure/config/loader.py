"""Configuration loader implementation using Pydantic Settings."""

from typing import Any
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from yukinoaaa.application.interfaces.config import IConfig


class Settings(BaseSettings, IConfig):
    """Application settings loaded from environment variables and .env file."""

    app_env: str = Field(default="development", description="Environment mode: development, staging, production")
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging severity level")
    database_url: str = Field(
        default="sqlite+aiosqlite:///:memory:",
        description="Async database connection URL",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )
    yukinoaaa_host: str = Field(
        default="0.0.0.0",
        description="API Server bind host",
    )
    yukinoaaa_port: int = Field(
        default=8000,
        description="API Server bind port",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a configuration value by attribute key."""
        return getattr(self, key, default)

    def get_database_url(self) -> str:
        """Retrieve the async database connection URL."""
        return self.database_url

    def get_redis_url(self) -> str:
        """Retrieve the redis connection URL."""
        return self.redis_url

    def is_production(self) -> bool:
        """Check if the application is running in production mode."""
        return self.app_env.lower() == "production"

    def is_debug(self) -> bool:
        """Check if debug mode is enabled."""
        return self.debug
