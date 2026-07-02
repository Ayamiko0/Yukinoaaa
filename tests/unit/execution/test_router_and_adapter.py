"""Tests for Order Router and Mock Execution Adapter."""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import pytest
from yukinoaaa.application.execution.router import OrderRouter
from yukinoaaa.application.trading.portfolio_service import PortfolioService
from yukinoaaa.domain.events import DomainEvent
from yukinoaaa.domain.execution.models import ExecutionState
from yukinoaaa.domain.trading.events import OrderCreatedEvent
from yukinoaaa.domain.trading.models import Order, OrderSide, OrderType
from yukinoaaa.infrastructure.cache.redis_cache import RedisCache
from yukinoaaa.infrastructure.events.event_bus import AsyncEventBus
from yukinoaaa.infrastructure.execution.mock_adapter import MockExecutionAdapter
from yukinoaaa.infrastructure.logging.logger import StructlogLogger


@pytest.mark.asyncio
async def test_order_router_dispatches_to_mock_adapter() -> None:
    """Verify router catches OrderCreatedEvent, submits to mock adapter, and emits ExecutionReportReceived."""
    logger = StructlogLogger()
    cache = RedisCache("redis://localhost:59999/0", logger)
    bus = AsyncEventBus(logger=logger)
    await bus.start()

    port_service = PortfolioService(cache, bus, logger, default_account_id="acc_router")
    adapter = MockExecutionAdapter(port_service, slippage_rate=Decimal("0.0"), fee_rate=Decimal("0.0"))
    router = OrderRouter(port_service, bus, logger)
    router.register_adapter("MOCK", adapter, is_default=True)

    reports_received: list[DomainEvent] = []

    async def on_rep(e: DomainEvent) -> None:
        reports_received.append(e)

    await bus.subscribe("ExecutionReportReceived", on_rep)
    await router.start()

    order = Order(
        symbol="BTC/USDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        price=Decimal("100000.0"),
        quantity=Decimal("0.5"),
    )
    port_service.portfolio.add_order(order)

    # Trigger routing
    await bus.publish(
        OrderCreatedEvent(
            event_type="OrderCreated",
            payload={"order_id": order.id, "symbol": order.symbol, "adapter": "MOCK"},
            timestamp=datetime.now(timezone.utc),
        )
    )
    await asyncio.sleep(0.05)

    assert len(reports_received) == 1
    assert reports_received[0].payload["status"] == ExecutionState.FILLED.value
    assert reports_received[0].payload["order_id"] == order.id

    await router.stop()
    await asyncio.sleep(0.05)
    await bus.stop()
    await cache.close()
