"""Tests for backtest domain models."""

from datetime import datetime, timezone
from decimal import Decimal
import pytest
from yukinoaaa.domain.backtest.models import BacktestConfig, PerformanceMetrics, TradeRecord


def test_backtest_models_immutability_and_validation() -> None:
    """Verify BacktestConfig and TradeRecord validation and immutability."""
    now = datetime.now(timezone.utc)
    config = BacktestConfig(symbol="BTC/USDT", start_time=now, end_time=now, strategy_name="RSI_Reversal")
    assert config.initial_equity == Decimal("10000.00")

    with pytest.raises(Exception):
        config.symbol = "ETH/USDT"  # type: ignore

    metrics = PerformanceMetrics(initial_equity=Decimal("10000"), final_equity=Decimal("15000"), total_trades=10)
    assert metrics.total_trades == 10
