"""Exponential Moving Average (EMA) indicator implementation."""

from decimal import Decimal
from yukinoaaa.application.interfaces.indicator import IIndicator
from yukinoaaa.domain.indicators.models import IndicatorValue
from yukinoaaa.domain.market.models import Kline


class EMA(IIndicator):
    """Exponential Moving Average with O(1) alpha weighting update."""

    def __init__(self, period: int = 20) -> None:
        """Initialize EMA alpha weighting multiplier and initial SMA warmup."""
        if period <= 0:
            raise ValueError("EMA period must be positive")
        self._period = period
        self._alpha = Decimal("2") / Decimal(str(period + 1))
        self._count = 0
        self._current_val: Decimal | None = None
        self._warmup_sum = Decimal("0")
        self._last_open_time = None
        self._last_confirmed_val: Decimal | None = None

    @property
    def name(self) -> str:
        return f"EMA_{self._period}"

    @property
    def period(self) -> int:
        return self._period

    @property
    def is_ready(self) -> bool:
        return self._count >= self._period

    def update(self, kline: Kline) -> IndicatorValue:
        """Update EMA with new candlestick closing price."""
        close_price = kline.close

        is_new_bar = self._last_open_time != kline.open_time
        if is_new_bar:
            if self._current_val is not None:
                self._last_confirmed_val = self._current_val
            self._count += 1
            self._last_open_time = kline.open_time

        if self._count < self._period:
            if is_new_bar:
                self._warmup_sum += close_price
            val = self._warmup_sum / Decimal(str(self._count))
            self._current_val = val
        elif self._count == self._period:
            if is_new_bar:
                self._warmup_sum += close_price
            val = self._warmup_sum / Decimal(str(self._period))
            self._current_val = val
            self._last_confirmed_val = val
        else:
            prev = self._last_confirmed_val if self._last_confirmed_val is not None else close_price
            val = (close_price - prev) * self._alpha + prev
            self._current_val = val

        return IndicatorValue(
            name=self.name,
            symbol=kline.symbol,
            timeframe=kline.timeframe,
            timestamp=kline.close_time,
            values={"value": round(self._current_val, 6)},
            is_ready=self.is_ready,
        )

    def reset(self) -> None:
        """Reset EMA calculation state."""
        self._count = 0
        self._current_val = None
        self._warmup_sum = Decimal("0")
        self._last_open_time = None
        self._last_confirmed_val = None
