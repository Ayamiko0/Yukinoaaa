"""Tests for Risk Engine orchestrator."""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import pytest
from yukinoaaa.application.risk.engine import RiskEngine
from yukinoaaa.application.risk.sizing import PositionCalculator
from yukinoaaa.application.risk.validator import RiskValidator
from yukinoaaa.application.trading.portfolio_service import PortfolioService
from yukinoaaa.domain.events import DomainEvent
from yukinoaaa.domain.risk.models import RiskPolicy, RiskStatus
from yukinoaaa.domain.trading.events import PositionClosedEvent, SignalCreatedEvent
from yukinoaaa.infrastructure.cache.redis_cache import RedisCache
from yukinoaaa.infrastructure.events.event_bus import AsyncEventBus
from yukinoaaa.infrastructure.logging.logger import StructlogLogger


@pytest.mark.asyncio
async def test_risk_engine_orchestration_and_emergency_halt() -> None:
    """Verify engine evaluates trade signals, registers approved orders, and halts on loss limits."""
    logger = StructlogLogger()
    cache = RedisCache("redis://localhost:59999/0", logger)
    bus = AsyncEventBus(logger=logger)
    await bus.start()

    port_service = PortfolioService(cache, bus, logger, default_account_id="acc_risk")
    policy = RiskPolicy(max_daily_loss_percent=Decimal("0.05"))
    validator = RiskValidator(policy, PositionCalculator())
    engine = RiskEngine(port_service, validator, policy, bus, logger)

    risk_events: list[DomainEvent] = []
    order_events: list[DomainEvent] = []

    async def on_risk(e: DomainEvent) -> None:
        risk_events.append(e)

    async def on_order(e: DomainEvent) -> None:
        order_events.append(e)

    await bus.subscribe("RiskEvaluated", on_risk)
    await bus.subscribe("RiskLimitExceeded", on_risk)
    await bus.subscribe("TradingHalted", on_risk)
    await bus.subscribe("OrderCreated", on_order)
    await engine.start()

    # Emit signal -> should evaluate to APPROVED and create Order
    await bus.publish(
        SignalCreatedEvent(
            event_type="SignalCreated",
            payload={
                "signal_id": "sig_001",
                "symbol": "BTC/USDT",
                "timeframe": "1m",
                "price": "100.0",
                "side": "BUY",
                "strategy_name": "TestStrat",
                "target_price": "110.0",
                "stop_loss": "95.0",
            },
            timestamp=datetime.now(timezone.utc),
        )
    )
    await asyncio.sleep(0.05)

    assert any(e.event_type == "RiskEvaluated" for e in risk_events)
    assert len(order_events) == 1
    assert len(port_service.portfolio.orders) == 1

    # Simulate major loss on position close exceeding 5% daily limit -> triggers EMERGENCY HALT
    await bus.publish(
        PositionClosedEvent(
            event_type="PositionClosed",
            payload={
                "account_id": "acc_risk",
                "position_id": "pos_1",
                "symbol": "BTC/USDT",
                "realized_pnl": "-6000.0",  # 6,000 / 100,000 = 6% loss > 5% limit
            },
            timestamp=datetime.now(timezone.utc),
        )
    )
    await asyncio.sleep(0.05)

    assert engine.is_halted is True
    assert any(e.event_type == "RiskLimitExceeded" for e in risk_events)
    assert any(e.event_type == "TradingHalted" for e in risk_events)

    await engine.stop()
    await asyncio.sleep(0.05)
    await bus.stop()
    await cache.close()
