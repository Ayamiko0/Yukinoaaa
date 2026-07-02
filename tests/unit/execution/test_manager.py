"""Tests for Order Manager state synchronization engine."""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from yukinoaaa.application.execution.manager import OrderManager
from yukinoaaa.application.trading.portfolio_service import PortfolioService
from yukinoaaa.domain.events import DomainEvent
from yukinoaaa.domain.execution.events import ExecutionReportReceivedEvent
from yukinoaaa.domain.execution.models import ExecutionState
from yukinoaaa.domain.trading.models import Order, OrderSide, OrderType
from yukinoaaa.infrastructure.cache.redis_cache import RedisCache
from yukinoaaa.infrastructure.events.event_bus import AsyncEventBus
from yukinoaaa.infrastructure.logging.logger import StructlogLogger


@pytest.mark.asyncio
async def test_order_manager_synchronizes_state_and_opens_position() -> None:
    """Verify manager updates order status on execution reports and registers position upon FILLED status."""
    logger = StructlogLogger()
    cache = RedisCache("redis://localhost:59999/0", logger)
    bus = AsyncEventBus(logger=logger)
    await bus.start()

    port_service = PortfolioService(cache, bus, logger, default_account_id="acc_exec")
    manager = OrderManager(port_service, bus, logger)

    completed_events: list[DomainEvent] = []
    partial_events: list[DomainEvent] = []
    filled_events: list[DomainEvent] = []

    async def on_comp(e: DomainEvent) -> None:
        completed_events.append(e)

    async def on_part(e: DomainEvent) -> None:
        partial_events.append(e)

    async def on_fill(e: DomainEvent) -> None:
        filled_events.append(e)

    await bus.subscribe("OrderExecutionCompleted", on_comp)
    await bus.subscribe("OrderPartiallyFilled", on_part)
    await bus.subscribe("OrderFilled", on_fill)
    await manager.start()

    order = Order(
        symbol="SOL/USDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        price=Decimal("150.0"),
        quantity=Decimal("10.0"),
    )
    port_service.portfolio.add_order(order)

    # 1. Partial fill report
    await bus.publish(
        ExecutionReportReceivedEvent(
            event_type="ExecutionReportReceived",
            payload={
                "report_id": "rep_1",
                "order_id": order.id,
                "symbol": order.symbol,
                "status": ExecutionState.PARTIAL_FILLED.value,
                "filled_quantity": "4.0",
                "remaining_quantity": "6.0",
                "average_price": "150.0",
                "fee": "0.6",
            },
            timestamp=datetime.now(UTC),
        )
    )
    await asyncio.sleep(0.05)
    assert len(partial_events) == 1
    assert order.filled_quantity == Decimal("4.0")
    assert len(manager.get_active_orders("SOL/USDT")) == 1

    # 2. Complete fill report
    await bus.publish(
        ExecutionReportReceivedEvent(
            event_type="ExecutionReportReceived",
            payload={
                "report_id": "rep_2",
                "order_id": order.id,
                "symbol": order.symbol,
                "status": ExecutionState.FILLED.value,
                "filled_quantity": "10.0",
                "remaining_quantity": "0.0",
                "average_price": "150.0",
                "fee": "1.5",
            },
            timestamp=datetime.now(UTC),
        )
    )
    await asyncio.sleep(0.05)

    assert len(filled_events) == 1
    assert len(completed_events) == 1
    assert len(manager.get_active_orders("SOL/USDT")) == 0
    assert "SOL/USDT" in port_service.portfolio.positions
    assert port_service.portfolio.positions["SOL/USDT"].quantity == Decimal("10.0")

    await manager.stop()
    await asyncio.sleep(0.05)
    await bus.stop()
    await cache.close()
