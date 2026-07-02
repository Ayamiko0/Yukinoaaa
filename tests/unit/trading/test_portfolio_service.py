"""Tests for Portfolio Service orchestrator."""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from yukinoaaa.application.trading.portfolio_service import PortfolioService
from yukinoaaa.domain.events import DomainEvent
from yukinoaaa.domain.market.events import TickReceivedEvent
from yukinoaaa.domain.trading.models import Position, PositionSide
from yukinoaaa.infrastructure.cache.redis_cache import RedisCache
from yukinoaaa.infrastructure.events.event_bus import AsyncEventBus
from yukinoaaa.infrastructure.logging.logger import StructlogLogger


@pytest.mark.asyncio
async def test_portfolio_service_tick_updates_and_events() -> None:
    """Verify service updates open position mark prices when ticks arrive and emits lifecycle events."""
    logger = StructlogLogger()
    cache = RedisCache(redis_url="redis://localhost:59999/0", logger=logger)
    bus = AsyncEventBus(logger=logger)
    await bus.start()

    service = PortfolioService(cache=cache, event_bus=bus, logger=logger, default_account_id="acc123")

    events_received: list[DomainEvent] = []

    async def on_event(e: DomainEvent) -> None:
        events_received.append(e)

    await bus.subscribe("PositionOpened", on_event)
    await bus.subscribe("PositionClosed", on_event)
    await service.start()

    pos = Position(
        symbol="BTC/USDT",
        side=PositionSide.LONG,
        entry_price=Decimal("95000"),
        mark_price=Decimal("95000"),
        quantity=Decimal("1.0"),
    )
    await service.open_position(pos, required_margin=Decimal("10000"))
    await asyncio.sleep(0.05)
    assert any(e.event_type == "PositionOpened" for e in events_received)

    # Publish real-time tick -> should update position mark price
    await bus.publish(
        TickReceivedEvent(
            event_type="TickReceived",
            payload={"symbol": "BTC/USDT", "price": "96000", "volume": "0.5"},
            timestamp=datetime.now(UTC),
        )
    )
    await asyncio.sleep(0.05)

    assert service.portfolio.positions["BTC/USDT"].mark_price == Decimal("96000")
    assert service.portfolio.positions["BTC/USDT"].unrealized_pnl == Decimal("1000")

    await service.close_position("BTC/USDT", Decimal("96000"))
    await asyncio.sleep(0.05)
    assert any(e.event_type == "PositionClosed" for e in events_received)

    await service.stop()
    await asyncio.sleep(0.05)
    await bus.stop()
    await cache.close()
