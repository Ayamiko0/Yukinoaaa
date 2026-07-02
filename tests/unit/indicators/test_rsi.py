"""Tests for Relative Strength Index (RSI) indicator."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from yukinoaaa.application.indicators.rsi import RSI
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


def test_rsi_bounds_and_smoothing() -> None:
    """Verify RSI remains bounded within [0, 100] during trending sequences."""
    rsi = RSI(period=3)
    assert rsi.name == "RSI_3"

    with pytest.raises(ValueError):
        RSI(period=-1)

    prices = ["100", "102", "105", "104", "108", "107", "110", "112"]
    for i, p in enumerate(prices):
        res = rsi.update(_make_kline(p, minutes_ago=len(prices) - i))
        val = Decimal(str(res.values["rsi"]))
        assert Decimal("0") <= val <= Decimal("100")

    assert rsi.is_ready is True
    rsi.reset()
    assert rsi.is_ready is False
