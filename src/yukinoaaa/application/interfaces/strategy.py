"""Abstract interface contract for quantitative trading strategies."""

from abc import ABC, abstractmethod
from typing import Any

from yukinoaaa.domain.market.models import MarketSnapshot
from yukinoaaa.domain.trading.models import TradeSignal


class IStrategy(ABC):
    """Abstract base class for quantitative trading strategy plugins."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return unique identifier string of the strategy (e.g., 'RSI_Reversal_V1')."""
        ...

    @property
    @abstractmethod
    def symbol(self) -> str:
        """Return target market symbol string (e.g., 'BTC/USDT')."""
        ...

    @property
    @abstractmethod
    def timeframe(self) -> str:
        """Return target timeframe string (e.g., '1m', '1h')."""
        ...

    @abstractmethod
    def on_indicator_updated(self, indicator_name: str, values: dict[str, Any]) -> TradeSignal | None:
        """Evaluate strategy logic when a technical indicator is updated.

        Returns TradeSignal if entry/exit setup is confirmed, or None.
        """
        ...

    @abstractmethod
    def on_market_snapshot(self, snapshot: MarketSnapshot) -> TradeSignal | None:
        """Evaluate strategy logic when a new market snapshot is published."""
        ...
