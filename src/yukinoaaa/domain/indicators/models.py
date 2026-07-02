"""Immutable domain models for technical indicator values."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class IndicatorValue(BaseModel):
    """Immutable result representing the state of a technical indicator at a point in time."""

    name: str = Field(..., description="Name of the indicator, e.g., 'RSI_14', 'EMA_200', 'MACD_12_26_9'")
    symbol: str = Field(..., description="Standardized symbol string, e.g., 'BTC/USDT'")
    timeframe: str = Field(..., description="Timeframe interval string, e.g., '1m', '1h', '1d'")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the calculation (usually closing time of candlestick)",
    )
    values: dict[str, Decimal | float | int] = Field(
        ..., description="Dictionary of indicator output values, e.g., {'rsi': 65.4} or {'macd': 12.5, 'signal': 10.1}"
    )
    is_ready: bool = Field(
        default=True,
        description="Whether the indicator has processed enough historical periods to produce reliable values",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Optional calculation metadata or diagnostics"
    )

    model_config = ConfigDict(frozen=True)

    def get_value(self, key: str = "value", default: Decimal | float | int | None = None) -> Decimal | float | int | None:
        """Retrieve a specific output value by key."""
        return self.values.get(key, default)
