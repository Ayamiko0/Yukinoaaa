"""Global pytest fixtures."""

import pytest

from yukinoaaa.infrastructure.config.loader import Settings
from yukinoaaa.infrastructure.events.event_bus import AsyncEventBus
from yukinoaaa.infrastructure.logging.logger import StructlogLogger


@pytest.fixture
def test_config() -> Settings:
    """Provide a default test configuration."""
    return Settings(
        app_env="test",
        debug=True,
        log_level="DEBUG",
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="redis://localhost:6379/15",
    )


@pytest.fixture
def test_logger() -> StructlogLogger:
    """Provide a test logger instance."""
    return StructlogLogger(log_level="DEBUG", is_production=False)


@pytest.fixture
def test_event_bus(test_logger: StructlogLogger) -> AsyncEventBus:
    """Provide an unstarted async event bus instance."""
    return AsyncEventBus(logger=test_logger)
