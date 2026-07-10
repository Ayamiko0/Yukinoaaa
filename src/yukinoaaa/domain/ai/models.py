"""Domain models representing AI quantitative analysis context and results."""

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class SentimentType(StrEnum):
    """Sentiment classification produced by quantitative LLM analysis."""

    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class MarketContextSnapshot(BaseModel):
    """Snapshot of market indicators and portfolio health passed to AI for inference."""

    symbol: str = Field(..., description="Standardized symbol, e.g. 'BTC/USDT'")
    current_price: Decimal = Field(..., gt=0)
    rsi_14: float | None = Field(default=None, description="RSI indicator value")
    macd_line: float | None = Field(default=None, description="MACD line value")
    macd_signal: float | None = Field(default=None, description="MACD signal line value")
    price_change_24h_pct: float = Field(default=0.0, description="Estimated 24h price change percentage")
    active_position_side: str | None = Field(default=None, description="Active position side if open")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = ConfigDict(frozen=True)


class AIAnalysisResult(BaseModel):
    """Structured AI quantitative analysis output."""

    symbol: str = Field(...)
    model_name: str = Field(..., description="Local LLM model name, e.g. gemma3")
    sentiment: SentimentType = Field(default=SentimentType.NEUTRAL)
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    summary: str = Field(..., description="Concise executive summary of market conditions")
    key_factors: list[str] = Field(default_factory=list, description="Key driving technical factors")
    recommendation: str = Field(
        default="HOLD", description="Actionable quantitative recommendation: BUY, SELL, or HOLD"
    )
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = ConfigDict(frozen=True)
