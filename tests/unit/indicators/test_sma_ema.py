"""Tests for SMA and EMA indicator implementations."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from yukinoaaa.application.indicators.ema import EMA
from yukinoaaa.application.indicators.sma import SMA
from yukinoaaa.domain.market.models import Kline


def _make_kline(close: str, minutes_ago: int = 0) -> Kline:
    now = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    val = Decimal(close)
    return Kline(
        symbol="BTC/USDT",
        timeframe="1m",
        open_time=now - timedelta(minutes=1),
        close_time=now,
        open=val,
        high=val,
        low=val,
        close=val,
    )


def test_sma_sliding_window_accuracy() -> None:
    """Verify SMA running sum and sliding window removal."""
    sma = SMA(period=3)
    assert sma.name == "SMA_3"
    assert sma.is_ready is False

    res1 = sma.update(_make_kline("10", minutes_ago=3))
    assert res1.values["value"] == Decimal("10.000000")
    assert sma.is_ready is False

    sma.update(_make_kline("20", minutes_ago=2))
    res3 = sma.update(_make_kline("30", minutes_ago=1))
    assert res3.values["value"] == Decimal("20.000000")  # (10+20+30)/3 = 20
    assert sma.is_ready is True

    # Next kline should push out 10: (20+30+40)/3 = 30
    res4 = sma.update(_make_kline("40", minutes_ago=0))
    assert res4.values["value"] == Decimal("30.000000")


def test_ema_alpha_weighting_accuracy() -> None:
    """Verify EMA warmup and exponential alpha decay calculation."""
    ema = EMA(period=3)
    assert ema.name == "EMA_3"

    with pytest.raises(ValueError):
        EMA(period=0)

    ema.update(_make_kline("10", minutes_ago=3))
    ema.update(_make_kline("20", minutes_ago=2))
    res3 = ema.update(_make_kline("30", minutes_ago=1))
    # Warmup SMA = (10+20+30)/3 = 20
    assert res3.values["value"] == Decimal("20.000000")
    assert ema.is_ready is True

    # Next kline: alpha = 2/(3+1) = 0.5. EMA = (40 - 20)*0.5 + 20 = 30
    res4 = ema.update(_make_kline("40", minutes_ago=0))
    assert res4.values["value"] == Decimal("30.000000")

    ema.reset()
    assert ema.is_ready is False
