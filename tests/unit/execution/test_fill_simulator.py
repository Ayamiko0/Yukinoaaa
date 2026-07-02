"""Tests for real-time Fill Simulator."""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import pytest
from yukinoaaa.domain.events import DomainEvent
from yukinoaaa.domain.execution.models import ExecutionState
from yukinoaaa.domain.market.events import TickReceivedEvent
from yukinoaaa.domain.trading.models import Order, OrderSide, OrderType
from yukinoaaa.infrastructure.events.event_bus import AsyncEventBus
from yukinoaaa.infrastructure.execution.fill_simulator import FillSimulator
from yukinoaaa.infrastructure.logging.logger import StructlogLogger


@pytest.mark.asyncio
async def test_fill_simulator_matches_limit_order_on_tick() -> None:
    """Verify pending LIMIT order triggers simulated execution when incoming tick price crosses limit threshold."""
    logger = StructlogLogger()
    bus = AsyncEventBus(logger=logger)
    await bus.start()

    simulator = FillSimulator(bus, logger, slippage_rate=Decimal("0.0"), fee_rate=Decimal("0.0"))

    reports: list[DomainEvent] = []

    async def on_rep(e: DomainEvent) -> None:
        reports.append(e)

    await bus.subscribe("ExecutionReportReceived", on_rep)
    await simulator.start()

    # LIMIT BUY at 90.0
    order = Order(
        symbol="ETH/USDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        price=Decimal("90.0"),
        quantity=Decimal("2.0"),
    )
    simulator.add_pending_order(order)
    assert len(simulator.pending_orders) == 1

    # Tick at 95.0 -> above limit, should NOT trigger
    await bus.publish(
        TickReceivedEvent(
            event_type="TickReceived",
            payload={"symbol": "ETH/USDT", "price": "95.0"},
            timestamp=datetime.now(timezone.utc),
        )
    )
    await asyncio.sleep(0.05)
    assert len(reports) == 0
    assert len(simulator.pending_orders) == 1

    # Tick at 89.5 -> crosses limit 90.0 -> should trigger fill!
    await bus.publish(
        TickReceivedEvent(
            event_type="TickReceived",
            payload={"symbol": "ETH/USDT", "price": "89.5"},
            timestamp=datetime.now(timezone.utc),
        )
    )
    await asyncio.sleep(0.05)

    assert len(reports) == 1
    assert reports[0].payload["status"] == ExecutionState.FILLED.value
    assert len(simulator.pending_orders) == 0

    await simulator.stop()
    await asyncio.sleep(0.05)
    await bus.stop()
