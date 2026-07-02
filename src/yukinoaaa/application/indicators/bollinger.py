"""Bollinger Bands indicator implementation."""

import math
from collections import deque
from decimal import Decimal

from yukinoaaa.application.interfaces.indicator import IIndicator
from yukinoaaa.domain.indicators.models import IndicatorValue
from yukinoaaa.domain.market.models import Kline


class BollingerBands(IIndicator):
    """Bollinger Bands (Middle SMA +- k * Standard Deviation)."""

    def __init__(self, period: int = 20, std_dev_multiplier: float = 2.0) -> None:
        """Initialize window queue and standard deviation multiplier."""
        if period <= 1:
            raise ValueError("Bollinger Bands period must be > 1")
        self._period = period
        self._multiplier = Decimal(str(std_dev_multiplier))
        self._window: deque[Decimal] = deque(maxlen=period)
        self._last_open_time = None

    @property
    def name(self) -> str:
        return f"BB_{self._period}_{self._multiplier}"

    @property
    def period(self) -> int:
        return self._period

    @property
    def is_ready(self) -> bool:
        return len(self._window) >= self._period

    def update(self, kline: Kline) -> IndicatorValue:
        """Update Bollinger Bands with closing price."""
        close_price = kline.close

        if self._last_open_time == kline.open_time and len(self._window) > 0:
            self._window.pop()
        self._window.append(close_price)
        self._last_open_time = kline.open_time

        n = len(self._window)
        if n == 0:
            mid = Decimal("0")
            std_dev = Decimal("0")
        else:
            mid = sum(self._window) / Decimal(str(n))
            variance = sum((x - mid) ** 2 for x in self._window) / Decimal(str(n))
            std_dev = Decimal(str(math.sqrt(float(variance))))

        upper = mid + (self._multiplier * std_dev)
        lower = mid - (self._multiplier * std_dev)
        width = (upper - lower) / mid if mid > 0 else Decimal("0")

        return IndicatorValue(
            name=self.name,
            symbol=kline.symbol,
            timeframe=kline.timeframe,
            timestamp=kline.close_time,
            values={
                "value": round(mid, 6),
                "middle": round(mid, 6),
                "upper": round(upper, 6),
                "lower": round(lower, 6),
                "width": round(width, 6),
            },
            is_ready=self.is_ready,
        )

    def reset(self) -> None:
        """Reset Bollinger Bands state."""
        self._window.clear()
        self._last_open_time = None
