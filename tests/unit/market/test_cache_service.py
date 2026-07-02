"""Tests for market cache service and event emitting."""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from yukinoaaa.application.market.cache_service import MarketCacheService
from yukinoaaa.domain.events import DomainEvent
from yukinoaaa.domain.market.models import Kline, Tick
from yukinoaaa.infrastructure.cache.redis_cache import RedisCache
from yukinoaaa.infrastructure.events.event_bus import AsyncEventBus
from yukinoaaa.infrastructure.logging.logger import StructlogLogger


@pytest.mark.asyncio
async def test_cache_service_process_tick_and_kline() -> None:
    """Verify processing tick and kline updates snapshot and emits events."""
    logger = StructlogLogger()
    cache = RedisCache(redis_url="redis://localhost:59999/0", logger=logger)
    bus = AsyncEventBus(logger=logger)
    await bus.start()

    service = MarketCacheService(cache=cache, event_bus=bus, logger=logger)

    received_events: list[DomainEvent] = []

    async def event_handler(event: DomainEvent) -> None:
        received_events.append(event)

    await bus.subscribe("TickReceived", event_handler)
    await bus.subscribe("KlineReceived", event_handler)

    now = datetime.now(UTC)
    tick = Tick(symbol="BTC/USDT", price=Decimal("95000"), volume=Decimal("2.0"), timestamp=now)
    snapshot = await service.process_tick(tick)
    assert snapshot.last_tick == tick
    assert snapshot.symbol == "BTC/USDT"

    kline = Kline(
        symbol="BTC/USDT",
        timeframe="1m",
        open_time=now,
        close_time=now,
        open=Decimal("94900"),
        high=Decimal("95100"),
        low=Decimal("94800"),
        close=Decimal("95000"),
    )
    snapshot_after_kline = await service.process_kline(kline)
    assert snapshot_after_kline.last_kline == kline
    assert snapshot_after_kline.last_tick == tick

    await asyncio.sleep(0.05)
    await bus.stop()
    await cache.close()

    assert len(received_events) >= 2
    assert any(e.event_type == "TickReceived" for e in received_events)
    assert any(e.event_type == "KlineReceived" for e in received_events)
