"""Tests for trading domain models: Position, Portfolio, and Order."""

from decimal import Decimal

import pytest

from yukinoaaa.domain.exceptions import ValidationException
from yukinoaaa.domain.trading.models import (
    Order,
    OrderSide,
    OrderType,
    Portfolio,
    Position,
    PositionSide,
)


def test_position_unrealized_pnl_calculation() -> None:
    """Verify LONG and SHORT positions compute unrealized PnL correctly when mark price changes."""
    long_pos = Position(
        symbol="BTC/USDT",
        side=PositionSide.LONG,
        entry_price=Decimal("100.0"),
        mark_price=Decimal("100.0"),
        quantity=Decimal("2.0"),
    )
    pnl = long_pos.update_mark_price(Decimal("110.0"))
    assert pnl == Decimal("20.00")  # (110 - 100) * 2
    assert long_pos.unrealized_pnl == Decimal("20.00")

    short_pos = Position(
        symbol="BTC/USDT",
        side=PositionSide.SHORT,
        entry_price=Decimal("100.0"),
        mark_price=Decimal("100.0"),
        quantity=Decimal("2.0"),
    )
    pnl_short = short_pos.update_mark_price(Decimal("90.0"))
    assert pnl_short == Decimal("20.00")  # (100 - 90) * 2

    with pytest.raises(ValidationException):
        long_pos.update_mark_price(Decimal("-10.0"))


def test_portfolio_invariants_and_position_lifecycle() -> None:
    """Verify Portfolio balance, margin allocation, and equity calculation invariants."""
    port = Portfolio(account_id="test_user", available_balance=Decimal("1000.0"))
    assert port.total_equity == Decimal("1000.0")

    pos = Position(
        symbol="ETH/USDT",
        side=PositionSide.LONG,
        entry_price=Decimal("2000.0"),
        mark_price=Decimal("2000.0"),
        quantity=Decimal("0.1"),  # total value = 200, margin required = 100 with 2x leverage
        leverage=Decimal("2.0"),
    )

    port.open_position(pos, required_margin=Decimal("100.0"))
    assert port.available_balance == Decimal("900.0")
    assert port.margin_used == Decimal("100.0")
    assert port.total_equity == Decimal("1000.0")

    # Price rises to 2500 -> PnL = (2500 - 2000) * 0.1 = 50
    port.update_position_price("ETH/USDT", Decimal("2500.0"))
    assert port.total_unrealized_pnl == Decimal("50.00")
    assert port.total_equity == Decimal("1050.00")

    closed_pos = port.close_position("ETH/USDT", Decimal("2500.0"))
    assert closed_pos.realized_pnl == Decimal("50.00")
    assert port.available_balance == Decimal("1050.00")
    assert port.margin_used == Decimal("0.0")
    assert len(port.positions) == 0

    with pytest.raises(ValidationException):
        port.close_position("NON_EXISTENT", Decimal("100.0"))


def test_order_creation_and_registration() -> None:
    """Verify Order entity creation and portfolio registration."""
    port = Portfolio(account_id="test_user", available_balance=Decimal("500.0"))
    order = Order(
        symbol="SOL/USDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        price=Decimal("150.0"),
        quantity=Decimal("1.0"),
    )
    port.add_order(order)
    assert order.id in port.orders
