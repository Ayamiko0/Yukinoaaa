"""Generic async base repository implementation using SQLAlchemy."""

from collections.abc import Sequence
from typing import Any, Generic, TypeVar
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from yukinoaaa.application.interfaces.database import IRepository

T = TypeVar("T")
ID = TypeVar("ID")


class BaseRepository(IRepository[T, ID], Generic[T, ID]):
    """Generic repository implementing basic CRUD operations."""

    def __init__(self, session: AsyncSession, model_class: type[T]) -> None:
        """Initialize repository with active async session and ORM model class."""
        self._session = session
        self._model_class = model_class

    async def add(self, entity: T) -> T:
        """Add and persist a new entity."""
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def get_by_id(self, entity_id: ID) -> T | None:
        """Fetch an entity by primary key."""
        result = await self._session.get(self._model_class, entity_id)
        return result

    async def list_all(self, limit: int = 100, offset: int = 0) -> Sequence[T]:
        """Fetch paginated entities."""
        stmt = select(self._model_class).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def update(self, entity: T) -> T:
        """Update entity state in session."""
        merged = await self._session.merge(entity)
        await self._session.flush()
        return merged

    async def delete(self, entity_id: ID) -> bool:
        """Delete entity by primary key."""
        entity = await self.get_by_id(entity_id)
        if entity is None:
            return False
        await self._session.delete(entity)
        await self._session.flush()
        return True
