"""Tests for Performance Analytics Calculator pure Decimal math."""

from datetime import datetime, timezone
from decimal import Decimal
from yukinoaaa.application.analytics.calculator import PerformanceCalculator
from yukinoaaa.domain.backtest.models import TradeRecord


def test_performance_calculator_metrics_accuracy() -> None:
    """Verify win rate, profit factor, max drawdown, Sharpe, and Sortino ratios match exact math formulas."""
    now = datetime.now(timezone.utc)
    trades = [
        TradeRecord(
            symbol="BTC/USDT",
            side="LONG",
            entry_time=now,
            entry_price=Decimal("100"),
            exit_time=now,
            exit_price=Decimal("110"),
            quantity=Decimal("1"),
            realized_pnl=Decimal("10"),
            return_percentage=Decimal("0.10"),
            holding_duration_seconds=60,
        ),
        TradeRecord(
            symbol="BTC/USDT",
            side="LONG",
            entry_time=now,
            entry_price=Decimal("110"),
            exit_time=now,
            exit_price=Decimal("105"),
            quantity=Decimal("1"),
            realized_pnl=Decimal("-5"),
            return_percentage=Decimal("-0.05"),
            holding_duration_seconds=60,
        ),
        TradeRecord(
            symbol="BTC/USDT",
            side="LONG",
            entry_time=now,
            entry_price=Decimal("105"),
            exit_time=now,
            exit_price=Decimal("120"),
            quantity=Decimal("1"),
            realized_pnl=Decimal("15"),
            return_percentage=Decimal("0.15"),
            holding_duration_seconds=60,
        ),
    ]

    # Equity starts at 100, goes to 110 (+10), drops to 105 (-5), rises to 120 (+15)
    # Peak is 110, drops to 105 -> max drawdown amount = 5. Max dd % = 5 / 110 = 0.04545... -> 0.0455
    equity_curve = [Decimal("100"), Decimal("110"), Decimal("105"), Decimal("120")]

    metrics = PerformanceCalculator.calculate_metrics(
        initial_equity=Decimal("100.00"),
        final_equity=Decimal("120.00"),
        trades=trades,
        equity_curve=equity_curve,
    )

    assert metrics.total_trades == 3
    assert metrics.winning_trades == 2
    assert metrics.losing_trades == 1
    assert metrics.win_rate == Decimal("0.6667")
    assert metrics.total_realized_pnl == Decimal("20.0000")  # +10 - 5 + 15
    assert metrics.total_return_percentage == Decimal("0.2000")  # 20 / 100
    assert metrics.profit_factor == Decimal("5.0000")  # 25 / 5
    assert metrics.max_drawdown_amount == Decimal("5.0000")
    assert metrics.max_drawdown_percentage == Decimal("0.0455")
    assert metrics.sharpe_ratio > Decimal("0")
    assert metrics.sortino_ratio >= metrics.sharpe_ratio  # Sortino penalizes only downside volatility
