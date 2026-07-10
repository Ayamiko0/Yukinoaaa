"""Tests for MACD, Bollinger Bands, and ATR indicators."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from yukinoaaa.application.indicators.atr import ATR
from yukinoaaa.application.indicators.bollinger import BollingerBands
from yukinoaaa.application.indicators.macd import MACD
from yukinoaaa.domain.market.models import Kline


def _make_kline(high: str, low: str, close: str, minutes_ago: int = 0) -> Kline:
    now = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    high_dec, low_dec, close_dec = Decimal(high), Decimal(low), Decimal(close)
    return Kline(
        symbol="BTC/USDT",
        timeframe="1m",
        open_time=now - timedelta(minutes=1),
        close_time=now,
        open=low_dec,
        high=high_dec,
        low=low_dec,
        close=close_dec,
    )


def test_macd_computation() -> None:
    """Verify MACD line, signal line, and histogram computation."""
    macd = MACD(fast_period=3, slow_period=5, signal_period=2)
    assert macd.name == "MACD_3_5_2"

    with pytest.raises(ValueError):
        MACD(fast_period=10, slow_period=5)

    for i in range(10):
        res = macd.update(_make_kline("100", "90", str(100 + i), minutes_ago=10 - i))
        assert "macd" in res.values
        assert "signal" in res.values
        assert "histogram" in res.values

    assert macd.is_ready is True
    macd.reset()
    assert macd.is_ready is False


def test_bollinger_bands_width_and_std_dev() -> None:
    """Verify Bollinger Bands upper/lower standard deviation bounds."""
    bb = BollingerBands(period=3, std_dev_multiplier=2.0)
    assert bb.name == "BB_3_2.0"

    with pytest.raises(ValueError):
        BollingerBands(period=1)

    bb.update(_make_kline("10", "10", "10", minutes_ago=3))
    bb.update(_make_kline("10", "10", "10", minutes_ago=2))
    res = bb.update(_make_kline("10", "10", "10", minutes_ago=1))
    # When all prices are 10, std_dev is 0, so upper == lower == middle == 10
    assert res.values["middle"] == Decimal("10.000000")
    assert res.values["upper"] == Decimal("10.000000")
    assert res.values["lower"] == Decimal("10.000000")
    assert res.values["width"] == Decimal("0.000000")

    res2 = bb.update(_make_kline("20", "20", "20", minutes_ago=0))
    assert res2.values["upper"] > res2.values["middle"] > res2.values["lower"]
    bb.reset()


def test_atr_true_range_calculation() -> None:
    """Verify Average True Range correctly accounts for gap opens."""
    atr = ATR(period=3)
    assert atr.name == "ATR_3"

    with pytest.raises(ValueError):
        ATR(period=0)

    # Bar 1: H=10, L=5 -> TR = 5
    res1 = atr.update(_make_kline("10", "5", "8", minutes_ago=3))
    assert res1.values["true_range"] == Decimal("5.000000")

    # Bar 2: H=15, L=12, PrevClose=8 -> TR = max(15-12, |15-8|, |12-8|) = max(3, 7, 4) = 7
    res2 = atr.update(_make_kline("15", "12", "14", minutes_ago=2))
    assert res2.values["true_range"] == Decimal("7.000000")
