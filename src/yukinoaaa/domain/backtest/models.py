"""Backtest domain models: Config, TradeRecord, and PerformanceMetrics."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BacktestConfig(BaseModel):
    """Configuration parameters for an automated backtest simulation run."""
    backtest_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = Field(...)
    timeframe: str = Field(default="1m")
    start_time: datetime = Field(...)
    end_time: datetime = Field(...)
    initial_equity: Decimal = Field(default=Decimal("10000.00"), gt=0)
    strategy_name: str = Field(...)
    strategy_params: dict[str, Any] = Field(default_factory=dict)
    slippage_rate: Decimal = Field(default=Decimal("0.0005"), ge=0)
    fee_rate: Decimal = Field(default=Decimal("0.0010"), ge=0)

    model_config = ConfigDict(frozen=True)


class TradeRecord(BaseModel):
    """Immutable log of a completed, closed trading transaction."""
    trade_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = Field(...)
    side: str = Field(description="LONG or SHORT")
    entry_time: datetime = Field(...)
    entry_price: Decimal = Field(gt=0)
    exit_time: datetime = Field(...)
    exit_price: Decimal = Field(gt=0)
    quantity: Decimal = Field(gt=0)
    realized_pnl: Decimal = Field(...)
    return_percentage: Decimal = Field(description="Percentage return on required position margin")
    holding_duration_seconds: int = Field(ge=0)

    model_config = ConfigDict(frozen=True)


class PerformanceMetrics(BaseModel):
    """Quantitative analytics summary generated from backtest trade records and equity curve."""
    initial_equity: Decimal = Field(...)
    final_equity: Decimal = Field(...)
    total_return_percentage: Decimal = Field(default=Decimal("0.0"))
    total_trades: int = Field(default=0, ge=0)
    winning_trades: int = Field(default=0, ge=0)
    losing_trades: int = Field(default=0, ge=0)
    win_rate: Decimal = Field(default=Decimal("0.0"), ge=0, le=1)
    total_realized_pnl: Decimal = Field(default=Decimal("0.0"))
    max_drawdown_amount: Decimal = Field(default=Decimal("0.0"), ge=0)
    max_drawdown_percentage: Decimal = Field(default=Decimal("0.0"), ge=0)
    profit_factor: Decimal = Field(default=Decimal("0.0"), ge=0)
    sharpe_ratio: Decimal = Field(default=Decimal("0.0"))
    sortino_ratio: Decimal = Field(default=Decimal("0.0"))
    average_trade_pnl: Decimal = Field(default=Decimal("0.0"))
    largest_win: Decimal = Field(default=Decimal("0.0"))
    largest_loss: Decimal = Field(default=Decimal("0.0"))
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = ConfigDict(frozen=True)
