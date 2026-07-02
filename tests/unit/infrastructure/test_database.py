"""Tests for database session and repository."""

import pytest
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from yukinoaaa.infrastructure.database.repository import BaseRepository
from yukinoaaa.infrastructure.database.session import AsyncDatabase, Base
from yukinoaaa.infrastructure.logging.logger import StructlogLogger


class DummyModel(Base):
    """Dummy entity for testing BaseRepository."""

    __tablename__ = "dummy_models"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50))


@pytest.mark.asyncio
async def test_database_lifecycle_and_repository() -> None:
    """Verify engine connect, table creation, and CRUD via BaseRepository."""
    logger = StructlogLogger()
    db = AsyncDatabase(database_url="sqlite+aiosqlite:///:memory:", logger=logger)

    await db.connect()
    await db.create_all_tables()

    session_factory = db.get_session_factory()
    async with session_factory() as session:
        repo = BaseRepository(session=session, model_class=DummyModel)

        # Create / Add
        dummy = DummyModel(name="Test Yukinoaaa")
        added = await repo.add(dummy)
        await session.commit()
        assert added.id is not None
        assert added.name == "Test Yukinoaaa"

        # Get by ID
        fetched = await repo.get_by_id(added.id)
        assert fetched is not None
        assert fetched.name == "Test Yukinoaaa"

        # List all
        all_items = await repo.list_all()
        assert len(all_items) == 1

        # Update
        fetched.name = "Updated Yukinoaaa"
        updated = await repo.update(fetched)
        await session.commit()
        assert updated.name == "Updated Yukinoaaa"

        # Delete
        deleted = await repo.delete(added.id)
        await session.commit()
        assert deleted is True

        # Verify deletion
        not_found = await repo.get_by_id(added.id)
        assert not_found is None

        # Delete non-existent
        deleted_again = await repo.delete(9999)
        assert deleted_again is False

    await db.disconnect()


@pytest.mark.asyncio
async def test_database_unconnected_raises() -> None:
    """Verify calling get_session_factory without connect raises RuntimeError."""
    logger = StructlogLogger()
    db = AsyncDatabase(database_url="sqlite+aiosqlite:///:memory:", logger=logger)
    with pytest.raises(RuntimeError):
        db.get_session_factory()
