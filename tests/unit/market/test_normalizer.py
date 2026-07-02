"""Tests for market data normalizer and deduplication."""

from datetime import UTC, datetime
from decimal import Decimal

from yukinoaaa.application.market.normalizer import MarketNormalizer
from yukinoaaa.domain.market.models import Tick
from yukinoaaa.infrastructure.logging.logger import StructlogLogger


def test_normalizer_deduplication() -> None:
    """Verify duplicate ticks with same timestamp and price are discarded."""
    logger = StructlogLogger()
    normalizer = MarketNormalizer(logger=logger)

    now = datetime.now(UTC)
    tick1 = Tick(symbol="btc/usdt", price=Decimal("100"), volume=Decimal("1"), timestamp=now, exchange="binance")
    tick2 = Tick(symbol="BTC/USDT", price=Decimal("100"), volume=Decimal("1"), timestamp=now, exchange="binance")

    res1 = normalizer.normalize_and_deduplicate(tick1)
    assert res1 is not None
    assert res1.symbol == "BTC/USDT"  # Uppercase standardized

    res2 = normalizer.normalize_and_deduplicate(tick2)
    assert res2 is None  # Duplicate discarded


def test_normalizer_reset_state() -> None:
    """Verify resetting deduplication state allows processing tick again."""
    logger = StructlogLogger()
    normalizer = MarketNormalizer(logger=logger)

    now = datetime.now(UTC)
    tick = Tick(symbol="BTC/USDT", price=Decimal("100"), volume=Decimal("1"), timestamp=now, exchange="binance")
    normalizer.normalize_and_deduplicate(tick)

    normalizer.reset_state(symbol="BTC/USDT", exchange="binance")
    res_after = normalizer.normalize_and_deduplicate(tick)
    assert res_after is not None
