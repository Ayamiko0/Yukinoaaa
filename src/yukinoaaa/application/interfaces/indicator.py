"""Abstract interface contract for technical indicators."""

from abc import ABC, abstractmethod

from yukinoaaa.domain.indicators.models import IndicatorValue
from yukinoaaa.domain.market.models import Kline


class IIndicator(ABC):
    """Abstract base class for stateful, incremental technical indicator calculations."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return unique identifier string of the indicator (e.g., 'RSI_14', 'EMA_50')."""
        ...

    @property
    @abstractmethod
    def period(self) -> int:
        """Return primary lookback window period of the indicator."""
        ...

    @property
    @abstractmethod
    def is_ready(self) -> bool:
        """Check if indicator has processed sufficient historical candlesticks."""
        ...

    @abstractmethod
    def update(self, kline: Kline) -> IndicatorValue:
        """Process a candlestick bar and return updated indicator value."""
        ...

    @abstractmethod
    def reset(self) -> None:
        """Reset internal calculation state and historical buffers."""
        ...
