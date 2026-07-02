"""Tests for cache implementation."""

import pytest
from yukinoaaa.infrastructure.cache.redis_cache import RedisCache
from yukinoaaa.infrastructure.logging.logger import StructlogLogger


@pytest.mark.asyncio
async def test_redis_cache_memory_fallback() -> None:
    """Verify cache falls back to in-memory dictionary when Redis is unreachable."""
    logger = StructlogLogger()
    # Use an invalid/unreachable redis port to trigger fallback
    cache = RedisCache(redis_url="redis://localhost:59999/0", logger=logger)

    await cache.set("test_key", {"name": "Yukinoaaa", "version": 1})
    val = await cache.get("test_key")
    assert val == {"name": "Yukinoaaa", "version": 1}

    exists = await cache.exists("test_key")
    assert exists is True

    deleted = await cache.delete("test_key")
    assert deleted is True

    exists_after = await cache.exists("test_key")
    assert exists_after is False

    await cache.close()
