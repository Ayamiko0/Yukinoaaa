"""Configuration loader interface."""

from abc import ABC, abstractmethod
from typing import Any


class IConfig(ABC):
    """Abstract interface for configuration loading and management."""

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a configuration value by key."""
        ...

    @abstractmethod
    def get_database_url(self) -> str:
        """Retrieve the async database connection URL."""
        ...

    @abstractmethod
    def get_redis_url(self) -> str:
        """Retrieve the redis connection URL."""
        ...

    @abstractmethod
    def is_production(self) -> bool:
        """Check if the application is running in production mode."""
        ...

    @abstractmethod
    def is_debug(self) -> bool:
        """Check if debug mode is enabled."""
        ...
