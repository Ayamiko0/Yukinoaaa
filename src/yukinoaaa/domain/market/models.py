"""Immutable market data domain models and value objects."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Symbol(BaseModel):
    """Value object representing a standardized trading instrument pair."""

    base_asset: str = Field(..., description="Base asset symbol, e.g., 'BTC' or 'XAU'")
    quote_asset: str = Field(..., description="Quote asset symbol, e.g., 'USDT' or 'USD'")
    market_type: Literal["crypto", "forex", "metal"] = Field(
        default="crypto", description="Asset class / market category"
    )
    raw_symbol: str | None = Field(
        default=None, description="Original exchange-specific symbol string if mapped"
    )

    model_config = ConfigDict(frozen=True)

    @field_validator("base_asset", "quote_asset")
    @classmethod
    def uppercase_asset(cls, v: str) -> str:
        """Ensure asset names are uppercase and stripped."""
        val = v.strip().upper()
        if not val:
            raise ValueError("Asset symbol cannot be empty")
        return val

    @property
    def standardized(self) -> str:
        """Return canonical standard symbol string, e.g., 'BTC/USDT'."""
        return f"{self.base_asset}/{self.quote_asset}"

    def __str__(self) -> str:
        return self.standardized


class Tick(BaseModel):
    """Immutable real-time market price update (Ticker / Trade tick)."""

    symbol: str = Field(..., description="Standardized symbol string, e.g., 'BTC/USDT'")
    price: Decimal = Field(..., description="Last traded price")
    volume: Decimal = Field(default=Decimal("0.0"), description="Traded volume or 24h volume")
    bid: Decimal | None = Field(default=None, description="Current highest bid price")
    ask: Decimal | None = Field(default=None, description="Current lowest ask price")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp of the market tick",
    )
    exchange: str = Field(default="mock", description="Source exchange identifier")

    model_config = ConfigDict(frozen=True)

    @field_validator("price")
    @classmethod
    def positive_price(cls, v: Decimal) -> Decimal:
        """Ensure tick price is strictly positive."""
        if v <= Decimal("0"):
            raise ValueError(f"Tick price must be positive, got {v}")
        return v

    @field_validator("volume")
    @classmethod
    def non_negative_volume(cls, v: Decimal) -> Decimal:
        """Ensure traded volume is non-negative."""
        if v < Decimal("0"):
            raise ValueError(f"Tick volume cannot be negative, got {v}")
        return v


class Kline(BaseModel):
    """Immutable candlestick period bar data (Kline / OHLCV)."""

    symbol: str = Field(..., description="Standardized symbol string, e.g., 'BTC/USDT'")
    timeframe: str = Field(..., description="Timeframe interval string, e.g., '1m', '1h', '1d'")
    open_time: datetime = Field(..., description="Start UTC timestamp of the bar period")
    close_time: datetime = Field(..., description="End UTC timestamp of the bar period")
    open: Decimal = Field(..., description="Opening price")
    high: Decimal = Field(..., description="Highest price during period")
    low: Decimal = Field(..., description="Lowest price during period")
    close: Decimal = Field(..., description="Closing price")
    volume: Decimal = Field(default=Decimal("0.0"), description="Total volume during period")
    is_closed: bool = Field(default=True, description="Whether this candlestick period is completed")

    model_config = ConfigDict(frozen=True)

    @field_validator("open", "high", "low", "close")
    @classmethod
    def positive_prices(cls, v: Decimal) -> Decimal:
        """Ensure candlestick prices are positive."""
        if v <= Decimal("0"):
            raise ValueError(f"Kline price must be positive, got {v}")
        return v

    @field_validator("high")
    @classmethod
    def validate_high(cls, v: Decimal, info: Any) -> Decimal:
        """Ensure high price is at least open and low."""
        values = info.data
        if "open" in values and v < values["open"]:
            raise ValueError(f"High price ({v}) cannot be lower than open price ({values['open']})")
        if "low" in values and v < values["low"]:
            raise ValueError(f"High price ({v}) cannot be lower than low price ({values['low']})")
        return v


class OrderBookEntry(BaseModel):
    """Single price level entry in an order book."""

    price: Decimal = Field(..., description="Price level")
    amount: Decimal = Field(..., description="Available volume amount at this price level")

    model_config = ConfigDict(frozen=True)


class OrderBook(BaseModel):
    """Immutable snapshot of order book depth (bids and asks)."""

    symbol: str = Field(..., description="Standardized symbol string, e.g., 'BTC/USDT'")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp of the order book snapshot",
    )
    bids: list[OrderBookEntry] = Field(default_factory=list, description="Bids sorted best (highest) to worst")
    asks: list[OrderBookEntry] = Field(default_factory=list, description="Asks sorted best (lowest) to worst")
    exchange: str = Field(default="mock", description="Source exchange identifier")

    model_config = ConfigDict(frozen=True)

    @property
    def best_bid(self) -> Decimal | None:
        """Return highest bid price if book is not empty."""
        return self.bids[0].price if self.bids else None

    @property
    def best_ask(self) -> Decimal | None:
        """Return lowest ask price if book is not empty."""
        return self.asks[0].price if self.asks else None

    @property
    def spread(self) -> Decimal | None:
        """Return bid-ask spread if both best bid and best ask exist."""
        bid = self.best_bid
        ask = self.best_ask
        if bid is not None and ask is not None:
            return ask - bid
        return None


class MarketSnapshot(BaseModel):
    """Combined current real-time market state for a trading pair."""

    symbol: str = Field(..., description="Standardized symbol string")
    last_tick: Tick | None = Field(default=None, description="Most recent price tick")
    last_kline: Kline | None = Field(default=None, description="Most recent candlestick bar")
    orderbook: OrderBook | None = Field(default=None, description="Most recent order book depth")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when snapshot was compiled",
    )

    model_config = ConfigDict(frozen=True)
