"""Tests for technical indicator domain models."""

from decimal import Decimal
import pytest
from yukinoaaa.domain.indicators.models import IndicatorValue


def test_indicator_value_creation_and_helpers() -> None:
    """Verify IndicatorValue immutability and value retrieval methods."""
    val = IndicatorValue(
        name="RSI_14",
        symbol="BTC/USDT",
        timeframe="1m",
        values={"rsi": Decimal("65.40"), "value": Decimal("65.40")},
        is_ready=True,
    )
    assert val.name == "RSI_14"
    assert val.symbol == "BTC/USDT"
    assert val.get_value("rsi") == Decimal("65.40")
    assert val.get_value("missing", default=-1) == -1

    with pytest.raises(Exception):
        val.name = "RSI_21"  # type: ignore
