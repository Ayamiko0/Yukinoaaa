"""Tests for Position Sizing Calculator."""

from decimal import Decimal

import pytest

from yukinoaaa.application.risk.sizing import PositionCalculator
from yukinoaaa.domain.exceptions import ValidationException
from yukinoaaa.domain.risk.models import RiskPolicy
from yukinoaaa.domain.trading.models import OrderSide


def test_fixed_fractional_position_sizing_accuracy() -> None:
    """Verify order volume calculated from account equity and stop-loss distance matches formula."""
    policy = RiskPolicy(max_risk_per_trade_percent=Decimal("0.02"), max_position_size_usd=Decimal("100000.00"))

    # Equity = 10,000 -> Risk Amount = 200. Entry = 100, SL = 95 -> Distance = 5. Qty = 200 / 5 = 40.0
    qty, sl = PositionCalculator.calculate_position_size(
        equity=Decimal("10000.00"),
        entry_price=Decimal("100.00"),
        side=OrderSide.BUY,
        stop_loss=Decimal("95.00"),
        policy=policy,
    )
    assert qty == Decimal("40.000000")
    assert sl == Decimal("95.000000")

    # When Stop Loss is omitted, fallback uses default_stop_loss_percent (1.5% -> SL = 98.50, dist = 1.50)
    # Qty = 200 / 1.50 = 133.333333
    qty_fallback, sl_fallback = PositionCalculator.calculate_position_size(
        equity=Decimal("10000.00"),
        entry_price=Decimal("100.00"),
        side=OrderSide.BUY,
        stop_loss=None,
        policy=policy,
    )
    assert qty_fallback == Decimal("133.333333")
    assert sl_fallback == Decimal("98.500000")


def test_position_sizing_usd_cap_ceiling() -> None:
    """Verify position size is capped when raw value exceeds USD ceiling."""
    policy = RiskPolicy(max_risk_per_trade_percent=Decimal("0.10"), max_position_size_usd=Decimal("1000.00"))
    # Equity = 100,000 -> Risk Amount = 10,000. Entry = 100, SL = 99 -> Dist = 1. Raw Qty = 10,000.
    # USD Cap = 1000 / 100 = 10. Qty must be capped at 10.0
    qty, _ = PositionCalculator.calculate_position_size(
        equity=Decimal("100000.00"),
        entry_price=Decimal("100.00"),
        side=OrderSide.BUY,
        stop_loss=Decimal("99.00"),
        policy=policy,
    )
    assert qty == Decimal("10.000000")

    with pytest.raises(ValidationException):
        PositionCalculator.calculate_position_size(
            equity=Decimal("0.0"),
            entry_price=Decimal("100.0"),
            side=OrderSide.BUY,
            stop_loss=Decimal("95.0"),
            policy=policy,
        )
