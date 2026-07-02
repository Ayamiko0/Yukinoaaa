"""Tests for Historical Replay Engine."""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from yukinoaaa.domain.events import DomainEvent
from yukinoaaa.domain.market.models import Kline
from yukinoaaa.infrastructure.backtest.replay_engine import HistoricalReplayEngine
from yukinoaaa.infrastructure.events.event_bus import AsyncEventBus
from yukinoaaa.infrastructure.logging.logger import StructlogLogger


@pytest.mark.asyncio
async def test_replay_engine_pumps_klines_in_timestamp_order() -> None:
    """Verify replay engine sorts out-of-order klines and emits KlineReceived and TickReceived events."""
    logger = StructlogLogger()
    bus = AsyncEventBus(logger=logger)
    await bus.start()

    engine = HistoricalReplayEngine(bus, logger)

    kline_events: list[DomainEvent] = []
    tick_events: list[DomainEvent] = []

    async def on_k(e: DomainEvent) -> None:
        kline_events.append(e)

    async def on_t(e: DomainEvent) -> None:
        tick_events.append(e)

    await bus.subscribe("KlineReceived", on_k)
    await bus.subscribe("TickReceived", on_t)

    t1 = datetime.now(UTC)
    t2 = t1 + timedelta(minutes=1)

    k1 = Kline(symbol="BTC/USDT", timeframe="1m", open_time=t1, close_time=t1 + timedelta(seconds=59), open=Decimal("100"), high=Decimal("105"), low=Decimal("99"), close=Decimal("104"), volume=Decimal("10"))
    k2 = Kline(symbol="BTC/USDT", timeframe="1m", open_time=t2, close_time=t2 + timedelta(seconds=59), open=Decimal("104"), high=Decimal("110"), low=Decimal("103"), close=Decimal("108"), volume=Decimal("15"))

    # Pass out of order
    count = await engine.replay_klines([k2, k1], emit_ticks=True)
    await asyncio.sleep(0.05)

    assert count == 2
    assert len(kline_events) == 2
    assert len(tick_events) == 2
    # Check timestamp sorting
    assert kline_events[0].payload["close"] == "104"
    assert kline_events[1].payload["close"] == "108"

    await bus.stop()
