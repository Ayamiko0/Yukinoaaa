"""Tests for technical indicator engine orchestrator."""

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from yukinoaaa.application.indicators.engine import IndicatorEngine
from yukinoaaa.application.indicators.sma import SMA
from yukinoaaa.domain.events import DomainEvent
from yukinoaaa.domain.market.events import KlineReceivedEvent
from yukinoaaa.infrastructure.events.event_bus import AsyncEventBus
from yukinoaaa.infrastructure.logging.logger import StructlogLogger


@pytest.mark.asyncio
async def test_indicator_engine_event_orchestration() -> None:
    """Verify engine subscribes to KlineReceivedEvent, updates registered indicators, and emits IndicatorUpdatedEvent."""
    logger = StructlogLogger()
    bus = AsyncEventBus(logger=logger)
    await bus.start()

    engine = IndicatorEngine(event_bus=bus, logger=logger)
    sma = SMA(period=2)
    engine.register_indicator("BTC/USDT", "1m", sma)

    updated_events: list[DomainEvent] = []

    async def on_indicator_updated(e: DomainEvent) -> None:
        updated_events.append(e)

    await bus.subscribe("IndicatorUpdated", on_indicator_updated)
    await engine.start()

    now = datetime.now(timezone.utc)
    # Emit 1st kline
    await bus.publish(
        KlineReceivedEvent(
            event_type="KlineReceived",
            payload={"symbol": "BTC/USDT", "timeframe": "1m", "close": "100.0"},
            timestamp=now,
        )
    )
    await asyncio.sleep(0.05)
    assert sma.is_ready is False
    assert len(updated_events) == 0  # Not ready yet

    # Emit 2nd kline -> SMA is ready -> should emit IndicatorUpdatedEvent
    await bus.publish(
        KlineReceivedEvent(
            event_type="KlineReceived",
            payload={"symbol": "BTC/USDT", "timeframe": "1m", "close": "200.0"},
            timestamp=now + timedelta(minutes=1),
        )
    )
    await asyncio.sleep(0.05)

    assert sma.is_ready is True
    assert len(updated_events) >= 1
    assert updated_events[0].payload["indicator_name"] == "SMA_2"

    latest = engine.get_latest_value("BTC/USDT", "1m", "SMA_2")
    assert latest is not None
    assert latest.values["value"] == Decimal("150.000000")

    all_vals = engine.get_all_latest_values("BTC/USDT", "1m")
    assert "SMA_2" in all_vals

    await engine.stop()
    await asyncio.sleep(0.05)
    await bus.stop()
