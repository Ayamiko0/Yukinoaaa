"""Tests for market data domain models."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from yukinoaaa.domain.market.models import Kline, OrderBook, OrderBookEntry, Symbol, Tick


def test_symbol_standardized_format() -> None:
    """Verify symbol standard notation and validation."""
    sym = Symbol(base_asset="btc", quote_asset="usdt")
    assert sym.standardized == "BTC/USDT"
    assert str(sym) == "BTC/USDT"
    assert sym.market_type == "crypto"


def test_tick_validation() -> None:
    """Verify tick price/volume validation."""
    tick = Tick(
        symbol="BTC/USDT",
        price=Decimal("95000.00"),
        volume=Decimal("1.5"),
    )
    assert tick.price == Decimal("95000.00")

    with pytest.raises(ValueError):
        Tick(symbol="BTC/USDT", price=Decimal("-10.0"), volume=Decimal("1.0"))

    with pytest.raises(ValueError):
        Tick(symbol="BTC/USDT", price=Decimal("100.0"), volume=Decimal("-0.5"))


def test_kline_validation() -> None:
    """Verify kline high/low relationship."""
    now = datetime.now(UTC)
    kline = Kline(
        symbol="BTC/USDT",
        timeframe="1m",
        open_time=now - timedelta(minutes=1),
        close_time=now,
        open=Decimal("100"),
        high=Decimal("105"),
        low=Decimal("95"),
        close=Decimal("102"),
        volume=Decimal("10"),
    )
    assert kline.high >= kline.low
    assert kline.high >= kline.open

    with pytest.raises(ValueError):
        # High lower than open
        Kline(
            symbol="BTC/USDT",
            timeframe="1m",
            open_time=now - timedelta(minutes=1),
            close_time=now,
            open=Decimal("100"),
            high=Decimal("90"),
            low=Decimal("80"),
            close=Decimal("85"),
        )


def test_orderbook_spread_calculation() -> None:
    """Verify order book best bid/ask and spread computation."""
    ob = OrderBook(
        symbol="BTC/USDT",
        bids=[OrderBookEntry(price=Decimal("99.5"), amount=Decimal("1.0"))],
        asks=[OrderBookEntry(price=Decimal("100.5"), amount=Decimal("1.0"))],
    )
    assert ob.best_bid == Decimal("99.5")
    assert ob.best_ask == Decimal("100.5")
    assert ob.spread == Decimal("1.0")
