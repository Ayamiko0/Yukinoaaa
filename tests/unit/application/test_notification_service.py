"""Unit tests for application trading notification service."""

import pytest

from yukinoaaa.application.trading.notification_service import TradingNotificationService
from yukinoaaa.domain.trading.events import (
    OrderFilledEvent,
    PositionClosedEvent,
    PositionOpenedEvent,
    SignalCreatedEvent,
)
from yukinoaaa.infrastructure.discord.mock_adapter import MockDiscordAdapter
from yukinoaaa.infrastructure.events.event_bus import AsyncEventBus
from yukinoaaa.infrastructure.logging.logger import StructlogLogger


@pytest.mark.asyncio
async def test_trading_notification_service_event_dispatch() -> None:
    """Test that TradingNotificationService correctly receives domain events and emits Discord embeds."""
    logger = StructlogLogger()
    event_bus = AsyncEventBus(logger=logger)
    mock_discord = MockDiscordAdapter(logger=logger)
    service = TradingNotificationService(
        notification_service=mock_discord,
        event_bus=event_bus,
        logger=logger,
    )

    await event_bus.start()
    await service.start()
    await service.start()  # Idempotent

    # 1. Test OrderFilledEvent
    filled_event = OrderFilledEvent(
        event_type="OrderFilled",
        payload={
            "symbol": "BTC/USDT",
            "side": "BUY",
            "quantity": "0.5",
            "price": "68000",
            "order_id": "ord_1001",
        },
    )
    await event_bus.publish(filled_event)

    # 2. Test PositionOpenedEvent
    opened_event = PositionOpenedEvent(
        event_type="PositionOpened",
        payload={"symbol": "BTC/USDT", "side": "LONG", "size": "0.5", "entry_price": "68000"},
    )
    await event_bus.publish(opened_event)

    # 3. Test PositionClosedEvent (profit and loss scenarios)
    closed_event_win = PositionClosedEvent(
        event_type="PositionClosed",
        payload={
            "symbol": "BTC/USDT",
            "side": "LONG",
            "realized_pnl": "500.00",
            "exit_price": "69000",
        },
    )
    await event_bus.publish(closed_event_win)

    closed_event_loss = PositionClosedEvent(
        event_type="PositionClosed",
        payload={
            "symbol": "ETH/USDT",
            "side": "SHORT",
            "realized_pnl": "-120.00",
            "exit_price": "3500",
        },
    )
    await event_bus.publish(closed_event_loss)

    # 4. Test SignalCreatedEvent
    signal_event = SignalCreatedEvent(
        event_type="SignalCreated",
        payload={
            "symbol": "BTC/USDT",
            "strategy_id": "RSI_14",
            "direction": "BUY",
            "confidence": "85.0",
        },
    )
    await event_bus.publish(signal_event)

    signal_neutral = SignalCreatedEvent(
        event_type="SignalCreated",
        payload={
            "symbol": "BTC/USDT",
            "strategy_id": "RSI_14",
            "direction": "NEUTRAL",
            "confidence": "50.0",
        },
    )
    await event_bus.publish(signal_neutral)

    await event_bus._queue.join()

    assert len(mock_discord.sent_embeds) == 5
    assert mock_discord.sent_embeds[0]["title"] == "⚡ Order Successfully Filled"
    assert mock_discord.sent_embeds[1]["title"] == "🚀 Position Opened"
    assert "🏆" in mock_discord.sent_embeds[2]["title"]
    assert "🛡️" in mock_discord.sent_embeds[3]["title"]
    assert mock_discord.sent_embeds[4]["title"] == "🎯 Quantitative Strategy Signal"

    await service.stop()
    await service.stop()  # Idempotent
    await event_bus.stop()
