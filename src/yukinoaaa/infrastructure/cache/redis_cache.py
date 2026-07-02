"""Redis cache implementation with in-memory fallback."""

import json
from typing import Any
import redis.asyncio as redis
from yukinoaaa.application.interfaces.cache import ICache
from yukinoaaa.application.interfaces.logger import ILogger


class RedisCache(ICache):
    """Asynchronous caching service backed by Redis with in-memory dictionary fallback."""

    def __init__(self, redis_url: str, logger: ILogger) -> None:
        """Initialize Redis connection and in-memory fallback storage."""
        self._redis_url = redis_url
        self._logger = logger.bind(module="RedisCache")
        self._client: redis.Redis | None = None
        self._memory_fallback: dict[str, Any] = {}
        self._use_fallback = False

    async def _get_client(self) -> redis.Redis | None:
        """Get or initialize the async Redis client."""
        if self._use_fallback:
            return None
        if self._client is None:
            try:
                self._client = redis.from_url(self._redis_url, decode_responses=True)
                await self._client.ping()  # Verify connection
                self._logger.info("Connected to Redis successfully", url=self._redis_url)
            except Exception as e:
                self._logger.warning(
                    "Failed to connect to Redis. Switching to in-memory fallback cache.",
                    error=str(e),
                )
                self._use_fallback = True
                self._client = None
        return self._client

    async def get(self, key: str) -> Any | None:
        """Retrieve a cached value by key."""
        client = await self._get_client()
        if client is None:
            return self._memory_fallback.get(key)
        try:
            val = await client.get(key)
            if val is not None:
                try:
                    return json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    return val
            return None
        except Exception as e:
            self._logger.error("Redis get error, falling back to memory", key=key, error=str(e))
            self._use_fallback = True
            return self._memory_fallback.get(key)

    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        """Store a value in cache with optional TTL."""
        client = await self._get_client()
        serialized = json.dumps(value) if not isinstance(value, str | int | float | bool) else str(value)
        if client is None:
            self._memory_fallback[key] = value
            return
        try:
            if ttl_seconds:
                await client.setex(key, ttl_seconds, serialized)
            else:
                await client.set(key, serialized)
        except Exception as e:
            self._logger.error("Redis set error, storing in memory fallback", key=key, error=str(e))
            self._use_fallback = True
            self._memory_fallback[key] = value

    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        client = await self._get_client()
        if client is None:
            return self._memory_fallback.pop(key, None) is not None
        try:
            res = await client.delete(key)
            return bool(res > 0)
        except Exception as e:
            self._logger.error("Redis delete error", key=key, error=str(e))
            self._use_fallback = True
            return self._memory_fallback.pop(key, None) is not None

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        client = await self._get_client()
        if client is None:
            return key in self._memory_fallback
        try:
            res = await client.exists(key)
            return bool(res > 0)
        except Exception as e:
            self._logger.error("Redis exists error", key=key, error=str(e))
            self._use_fallback = True
            return key in self._memory_fallback

    async def close(self) -> None:
        """Close Redis client connections."""
        if self._client:
            await self._client.aclose()
            self._logger.info("Redis cache connection closed")
