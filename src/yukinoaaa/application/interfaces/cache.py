"""Cache interface for Redis or in-memory caching."""

from abc import ABC, abstractmethod
from typing import Any


class ICache(ABC):
    """Abstract interface for asynchronous key-value caching."""

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """Retrieve a value from cache by key."""
        ...

    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        """Store a value in cache with an optional expiration time in seconds."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Remove a key from cache. Returns True if key existed and was deleted."""
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key currently exists in cache."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close cache connections cleanly."""
        ...
