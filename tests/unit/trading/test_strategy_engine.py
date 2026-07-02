"""Tests for Strategy Engine orchestrator."""

import asyncio
from datetime import UTC, datetime

import pytest

from yukinoaaa.application.trading.strategies.rsi_reversal import RsiReversalStrategy
from yukinoaaa.application.trading.strategy_engine import StrategyEngine
from yukinoaaa.domain.events import DomainEvent
from yukinoaaa.domain.indicators.events import IndicatorUpdatedEvent
from yukinoaaa.infrastructure.events.event_bus import AsyncEventBus
from yukinoaaa.infrastructure.logging.logger import StructlogLogger


@pytest.mark.asyncio
async def test_strategy_engine_evaluates_plugins_and_emits_signals() -> None:
    """Verify engine invokes strategy plugin on IndicatorUpdatedEvent and emits SignalCreatedEvent."""
    logger = StructlogLogger()
    bus = AsyncEventBus(logger=logger)
    await bus.start()

    engine = StrategyEngine(event_bus=bus, logger=logger)
    strat = RsiReversalStrategy(symbol="BTC/USDT", timeframe="1m", oversold_threshold=30.0)
    engine.register_strategy(strat)

    signals: list[DomainEvent] = []

    async def on_signal(e: DomainEvent) -> None:
        signals.append(e)

    await bus.subscribe("SignalCreated", on_signal)
    await engine.start()

    # Emit oversold RSI -> should generate BUY signal
    await bus.publish(
        IndicatorUpdatedEvent(
            event_type="IndicatorUpdated",
            payload={
                "symbol": "BTC/USDT",
                "timeframe": "1m",
                "indicator_name": "RSI_14",
                "values": {"rsi": "25.5"},
                "is_ready": True,
            },
            timestamp=datetime.now(UTC),
        )
    )
    await asyncio.sleep(0.05)

    assert len(signals) >= 1
    assert signals[0].payload["side"] == "BUY"
    assert signals[0].payload["strategy_name"] == "RSI_Reversal_RSI_14"

    await engine.stop()
    await asyncio.sleep(0.05)
    await bus.stop()
