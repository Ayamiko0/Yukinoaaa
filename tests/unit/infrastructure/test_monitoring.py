"""Tests for monitoring and health check service."""

import pytest
from yukinoaaa.infrastructure.cache.redis_cache import RedisCache
from yukinoaaa.infrastructure.logging.logger import StructlogLogger
from yukinoaaa.infrastructure.monitoring.health import HealthCheckService


@pytest.mark.asyncio
async def test_health_check_with_memory_fallback_cache() -> None:
    """Verify health check returns valid JSON diagnostics."""
    logger = StructlogLogger()
    cache = RedisCache(redis_url="redis://localhost:59999/0", logger=logger)
    health_service = HealthCheckService(cache=cache, logger=logger)

    report = await health_service.check_health()
    assert "status" in report
    assert "timestamp" in report
    assert "components" in report
    assert report["components"]["cache"]["status"] in ["up", "degraded", "down"]
    await cache.close()
