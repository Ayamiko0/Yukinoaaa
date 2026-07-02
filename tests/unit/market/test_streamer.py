"""Tests for market data streamer orchestrator."""

import asyncio
from decimal import Decimal
import pytest
from yukinoaaa.application.market.cache_service import MarketCacheService
from yukinoaaa.application.market.normalizer import MarketNormalizer
from yukinoaaa.application.market.streamer import MarketDataStreamer
from yukinoaaa.application.market.validator import MarketValidator
from yukinoaaa.domain.events import DomainEvent
from yukinoaaa.domain.market.models import Tick
from yukinoaaa.infrastructure.cache.redis_cache import RedisCache
from yukinoaaa.infrastructure.events.event_bus import AsyncEventBus
from yukinoaaa.infrastructure.exchange.mock_adapter import MockExchangeAdapter
from yukinoaaa.infrastructure.logging.logger import StructlogLogger


@pytest.mark.asyncio
async def test_streamer_lifecycle_and_reconnect() -> None:
    """Verify streamer starts, processes ticks into cache, and auto-reconnects on disconnection."""
    logger = StructlogLogger()
    cache = RedisCache(redis_url="redis://localhost:59999/0", logger=logger)
    bus = AsyncEventBus(logger=logger)
    await bus.start()

    adapter = MockExchangeAdapter(logger=logger, interval_seconds=0.05)
    cache_service = MarketCacheService(cache=cache, event_bus=bus, logger=logger)
    validator = MarketValidator(logger=logger)
    normalizer = MarketNormalizer(logger=logger)

    streamer = MarketDataStreamer(
        adapter=adapter,
        cache_service=cache_service,
        validator=validator,
        normalizer=normalizer,
        event_bus=bus,
        logger=logger,
        initial_backoff_seconds=0.05,
    )

    reconnected_events: list[DomainEvent] = []

    async def on_reconnected(e: DomainEvent) -> None:
        reconnected_events.append(e)

    await bus.subscribe("StreamReconnected", on_reconnected)

    await streamer.start(["BTC/USDT"])
    await asyncio.sleep(0.15)

    snapshot = await cache_service.get_snapshot("BTC/USDT")
    assert snapshot.last_tick is not None
    assert snapshot.last_tick.price > Decimal("0")

    # Simulate connection drop to trigger auto-reconnect
    streamer._trigger_reconnect("Simulated drop for test")
    await asyncio.sleep(0.15)

    assert len(reconnected_events) >= 1
    assert reconnected_events[0].payload["exchange"] == "mock"

    await streamer.stop()
    await bus.stop()
    await cache.close()
