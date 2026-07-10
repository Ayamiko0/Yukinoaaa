"""Tests for Backtest Orchestrator end-to-end execution and report formatting."""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from yukinoaaa.application.backtest.orchestrator import BacktestOrchestrator
from yukinoaaa.domain.backtest.models import BacktestConfig
from yukinoaaa.domain.market.models import Kline
from yukinoaaa.infrastructure.logging.logger import StructlogLogger


@pytest.mark.asyncio
async def test_backtest_orchestrator_execution_and_markdown_report() -> None:
    """Verify orchestrator runs simulation, collects equity curve, computes metrics, and generates markdown report."""
    logger = StructlogLogger()
    orchestrator = BacktestOrchestrator(logger, redis_url="redis://localhost:59999/0")

    now = datetime.now(UTC)
    config = BacktestConfig(
        symbol="SOL/USDT",
        timeframe="1m",
        start_time=now,
        end_time=now + timedelta(minutes=3),
        initial_equity=Decimal("10000.00"),
        strategy_name="RSI_Reversal",
    )

    klines = [
        Kline(
            symbol="SOL/USDT",
            timeframe="1m",
            open_time=now,
            close_time=now + timedelta(seconds=59),
            open=Decimal("100"),
            high=Decimal("152"),
            low=Decimal("149"),
            close=Decimal("151"),
            volume=Decimal("100"),
        ),
        Kline(
            symbol="SOL/USDT",
            timeframe="1m",
            open_time=now + timedelta(minutes=1),
            close_time=now + timedelta(minutes=1, seconds=59),
            open=Decimal("151"),
            high=Decimal("155"),
            low=Decimal("150"),
            close=Decimal("154"),
            volume=Decimal("120"),
        ),
    ]

    metrics = await orchestrator.run_backtest(config, klines)
    await asyncio.sleep(0.05)

    assert metrics.initial_equity == Decimal("10000.00")
    assert len(orchestrator.equity_curve) >= 2

    markdown = BacktestOrchestrator.generate_markdown_report(config, metrics)
    assert "# Quantitative Backtest Report" in markdown
    assert "SOL/USDT" in markdown
    assert "Sharpe Ratio" in markdown
