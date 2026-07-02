"""Async SQLAlchemy session and database lifecycle manager."""

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from yukinoaaa.application.interfaces.database import IDatabase
from yukinoaaa.application.interfaces.logger import ILogger


class Base(DeclarativeBase):
    """Base class for SQLAlchemy declarative ORM models."""


class AsyncDatabase(IDatabase):
    """Asynchronous database connection pool and session manager."""

    def __init__(self, database_url: str, logger: ILogger, echo: bool = False) -> None:
        """Initialize database engine configuration."""
        self._url = database_url
        self._logger = logger.bind(module="AsyncDatabase")
        self._echo = echo
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    async def connect(self) -> None:
        """Create async engine and session factory."""
        if self._engine is not None:
            return
        self._logger.info("Connecting to database", url=self._url.split("@")[-1])
        self._engine = create_async_engine(self._url, echo=self._echo, future=True)
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    async def disconnect(self) -> None:
        """Dispose database engine connections."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            self._logger.info("Database connections disposed")

    async def create_all_tables(self) -> None:
        """Create database schema tables (for dev/testing)."""
        if not self._engine:
            await self._connect_if_needed()
        assert self._engine is not None
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self._logger.info("Database tables verified/created")

    async def _connect_if_needed(self) -> None:
        """Ensure connection pool is active."""
        if self._engine is None:
            await self.connect()

    def get_session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Get the async session maker."""
        if self._session_factory is None:
            raise RuntimeError("Database is not connected. Call connect() first.")
        return self._session_factory
