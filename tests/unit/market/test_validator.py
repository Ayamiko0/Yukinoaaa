"""Tests for market data validator."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from yukinoaaa.application.market.validator import MarketValidator
from yukinoaaa.domain.market.models import Kline, Tick
from yukinoaaa.infrastructure.logging.logger import StructlogLogger


def test_validator_tick_integrity() -> None:
    """Verify tick validation catches crossed books and drift."""
    logger = StructlogLogger()
    validator = MarketValidator(logger=logger, max_future_drift_seconds=60)

    valid_tick = Tick(symbol="BTC/USDT", price=Decimal("100"), volume=Decimal("1"))
    assert validator.validate_tick(valid_tick) is True

    crossed_tick = Tick(
        symbol="BTC/USDT",
        price=Decimal("100"),
        volume=Decimal("1"),
        bid=Decimal("105"),
        ask=Decimal("100"),
    )
    assert validator.validate_tick(crossed_tick) is False

    future_tick = Tick(
        symbol="BTC/USDT",
        price=Decimal("100"),
        volume=Decimal("1"),
        timestamp=datetime.now(UTC) + timedelta(minutes=5),
    )
    assert validator.validate_tick(future_tick) is False


def test_validator_kline_integrity() -> None:
    """Verify kline validation catches open/close time order errors."""
    logger = StructlogLogger()
    validator = MarketValidator(logger=logger)

    now = datetime.now(UTC)
    invalid_kline = Kline(
        symbol="BTC/USDT",
        timeframe="1m",
        open_time=now,
        close_time=now - timedelta(minutes=1),  # close before open
        open=Decimal("10"),
        high=Decimal("15"),
        low=Decimal("5"),
        close=Decimal("12"),
    )
    assert validator.validate_kline(invalid_kline) is False
