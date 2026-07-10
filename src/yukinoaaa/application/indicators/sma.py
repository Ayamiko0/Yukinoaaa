"""Simple Moving Average (SMA) indicator implementation."""

from collections import deque
from decimal import Decimal
from typing import TYPE_CHECKING

from yukinoaaa.application.interfaces.indicator import IIndicator
from yukinoaaa.domain.indicators.models import IndicatorValue
from yukinoaaa.domain.market.models import Kline

if TYPE_CHECKING:
    from datetime import datetime


class SMA(IIndicator):
    """Simple Moving Average with O(1) sliding window sum."""

    def __init__(self, period: int = 20) -> None:
        """Initialize sliding window queue and running sum."""
        if period <= 0:
            raise ValueError("SMA period must be positive")
        self._period = period
        self._window: deque[Decimal] = deque(maxlen=period)
        self._running_sum = Decimal("0")
        self._last_open_time: datetime | None = None

    @property
    def name(self) -> str:
        return f"SMA_{self._period}"

    @property
    def period(self) -> int:
        return self._period

    @property
    def is_ready(self) -> bool:
        return len(self._window) >= self._period

    def update(self, kline: Kline) -> IndicatorValue:
        """Update SMA with new kline closing price."""
        close_price = kline.close

        # If same bar update (streaming incomplete kline), replace last element
        if self._last_open_time == kline.open_time and len(self._window) > 0:
            old_val = self._window.pop()
            self._running_sum -= old_val
            self._window.append(close_price)
            self._running_sum += close_price
        else:
            if len(self._window) == self._period:
                old_val = self._window[0]
                self._running_sum -= old_val
            self._window.append(close_price)
            self._running_sum += close_price
            self._last_open_time = kline.open_time

        val = self._running_sum / Decimal(str(len(self._window))) if self._window else Decimal("0")

        return IndicatorValue(
            name=self.name,
            symbol=kline.symbol,
            timeframe=kline.timeframe,
            timestamp=kline.close_time,
            values={"value": round(val, 6)},
            is_ready=self.is_ready,
        )

    def reset(self) -> None:
        """Clear window and reset running sum."""
        self._window.clear()
        self._running_sum = Decimal("0")
        self._last_open_time = None
