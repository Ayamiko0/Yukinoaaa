"""Tests for MockExchangeAdapter."""

import asyncio
from decimal import Decimal

import pytest

from yukinoaaa.domain.market.models import Tick
from yukinoaaa.infrastructure.exchange.mock_adapter import MockExchangeAdapter
from yukinoaaa.infrastructure.logging.logger import StructlogLogger


@pytest.mark.asyncio
async def test_mock_adapter_ticker_klines_orderbook() -> None:
    """Verify REST/RPC simulation methods return valid data."""
    logger = StructlogLogger()
    adapter = MockExchangeAdapter(logger=logger)

    await adapter.connect()
    assert adapter.is_connected() is True

    ticker = await adapter.get_ticker("BTC/USDT")
    assert ticker.symbol == "BTC/USDT"
    assert ticker.price > Decimal("0")

    klines = await adapter.get_klines("BTC/USDT", "1m", limit=10)
    assert len(klines) == 10
    assert klines[-1].close > Decimal("0")

    orderbook = await adapter.get_orderbook("BTC/USDT", limit=5)
    assert len(orderbook.bids) == 5
    assert len(orderbook.asks) == 5
    assert orderbook.best_bid is not None
    assert orderbook.best_ask is not None
    assert orderbook.best_ask > orderbook.best_bid

    await adapter.disconnect()
    assert adapter.is_connected() is False


@pytest.mark.asyncio
async def test_mock_adapter_streaming() -> None:
    """Verify background task streams ticks to subscribers."""
    logger = StructlogLogger()
    adapter = MockExchangeAdapter(logger=logger, interval_seconds=0.05)
    await adapter.connect()

    received_ticks: list[Tick] = []

    async def on_tick(t: Tick) -> None:
        received_ticks.append(t)

    await adapter.subscribe_ticks(["ETH/USDT"], on_tick)
    await asyncio.sleep(0.15)
    await adapter.unsubscribe_ticks(["ETH/USDT"])
    await adapter.disconnect()

    assert len(received_ticks) >= 1
    assert received_ticks[0].symbol == "ETH/USDT"
