"""Database and Repository interfaces."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Generic, TypeVar

T = TypeVar("T")
ID = TypeVar("ID")


class IDatabase(ABC):
    """Abstract interface for asynchronous database session and lifecycle management."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection pool to the database."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection pool and release database resources."""
        ...

    @abstractmethod
    async def create_all_tables(self) -> None:
        """Create database schema if it does not exist (primarily for dev/testing)."""
        ...


class IRepository(ABC, Generic[T, ID]):
    """Generic abstract repository interface for domain aggregates and entities."""

    @abstractmethod
    async def add(self, entity: T) -> T:
        """Add a new entity to the repository."""
        ...

    @abstractmethod
    async def get_by_id(self, entity_id: ID) -> T | None:
        """Retrieve an entity by its unique identifier."""
        ...

    @abstractmethod
    async def list_all(self, limit: int = 100, offset: int = 0) -> Sequence[T]:
        """Retrieve a paginated list of entities."""
        ...

    @abstractmethod
    async def update(self, entity: T) -> T:
        """Update an existing entity."""
        ...

    @abstractmethod
    async def delete(self, entity_id: ID) -> bool:
        """Delete an entity by its unique identifier. Returns True if deleted."""
        ...
