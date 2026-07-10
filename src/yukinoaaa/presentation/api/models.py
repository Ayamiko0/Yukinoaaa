"""API data transfer models for requests and responses."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ApiResponse(BaseModel):
    """Standard generic wrapper for all API endpoint responses."""

    status: str = Field(default="success", description="success or error")
    data: Any | None = Field(default=None)
    error: str | None = Field(default=None)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = ConfigDict(frozen=True)


class PositionSnapshot(BaseModel):
    """Snapshot of an active trading position for frontend display."""

    symbol: str = Field(...)
    side: str = Field(...)
    quantity: Decimal = Field(...)
    entry_price: Decimal = Field(...)
    current_price: Decimal = Field(...)
    unrealized_pnl: Decimal = Field(...)
    unrealized_pnl_percentage: Decimal = Field(...)

    model_config = ConfigDict(frozen=True)


class PortfolioResponse(BaseModel):
    """Real-time portfolio status response payload."""

    account_id: str = Field(...)
    available_balance: Decimal = Field(...)
    total_equity: Decimal = Field(...)
    positions: list[PositionSnapshot] = Field(default_factory=list)
    active_orders_count: int = Field(default=0, ge=0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = ConfigDict(frozen=True)


class BacktestRequest(BaseModel):
    """Request payload to trigger an automated backtest simulation."""

    symbol: str = Field(default="BTC/USDT")
    timeframe: str = Field(default="1m")
    initial_equity: Decimal = Field(default=Decimal("10000.00"), gt=0)
    strategy_name: str = Field(default="RSI_Reversal")
    slippage_rate: Decimal = Field(default=Decimal("0.0005"), ge=0)
    fee_rate: Decimal = Field(default=Decimal("0.0010"), ge=0)

    model_config = ConfigDict(frozen=True)


class AIAnalysisRequest(BaseModel):
    """Request payload to trigger local LLM quantitative market analysis."""

    symbol: str = Field(default="BTC/USDT")
    current_price: Decimal = Field(default=Decimal("95400.00"), gt=0)
    rsi_value: float | None = Field(default=42.5)
    macd_line: float | None = Field(default=120.5)
    macd_signal: float | None = Field(default=115.0)
    price_change_24h_pct: float = Field(default=2.45)

    model_config = ConfigDict(frozen=True)
