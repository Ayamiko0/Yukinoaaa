"""Moving Average Convergence Divergence (MACD) indicator implementation."""

from decimal import Decimal
from typing import TYPE_CHECKING

from yukinoaaa.application.indicators.ema import EMA
from yukinoaaa.application.interfaces.indicator import IIndicator
from yukinoaaa.domain.indicators.models import IndicatorValue
from yukinoaaa.domain.market.models import Kline

if TYPE_CHECKING:
    from datetime import datetime


class MACD(IIndicator):
    """MACD combining fast EMA (12), slow EMA (26), and signal EMA (9)."""

    def __init__(
        self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9
    ) -> None:
        """Initialize fast, slow, and signal EMA instances."""
        if fast_period >= slow_period:
            raise ValueError("Fast EMA period must be strictly less than Slow EMA period")
        self._fast_period = fast_period
        self._slow_period = slow_period
        self._signal_period = signal_period

        self._fast_ema = EMA(period=fast_period)
        self._slow_ema = EMA(period=slow_period)
        self._signal_alpha = Decimal("2") / Decimal(str(signal_period + 1))
        self._signal_val: Decimal | None = None
        self._count = 0
        self._last_open_time: datetime | None = None
        self._last_confirmed_signal: Decimal | None = None

    @property
    def name(self) -> str:
        return f"MACD_{self._fast_period}_{self._slow_period}_{self._signal_period}"

    @property
    def period(self) -> int:
        return self._slow_period

    @property
    def is_ready(self) -> bool:
        return (
            self._slow_ema.is_ready and self._count >= self._slow_period + self._signal_period - 1
        )

    def update(self, kline: Kline) -> IndicatorValue:
        """Update MACD line, signal line, and histogram."""
        fast_res = self._fast_ema.update(kline)
        slow_res = self._slow_ema.update(kline)

        fast_val = Decimal(str(fast_res.values["value"]))
        slow_val = Decimal(str(slow_res.values["value"]))
        macd_line = fast_val - slow_val

        is_new_bar = self._last_open_time != kline.open_time
        if is_new_bar:
            if self._signal_val is not None:
                self._last_confirmed_signal = self._signal_val
            self._count += 1
            self._last_open_time = kline.open_time

        if self._last_confirmed_signal is None:
            self._signal_val = macd_line
        else:
            self._signal_val = (
                macd_line - self._last_confirmed_signal
            ) * self._signal_alpha + self._last_confirmed_signal

        sig = self._signal_val
        hist = macd_line - sig

        return IndicatorValue(
            name=self.name,
            symbol=kline.symbol,
            timeframe=kline.timeframe,
            timestamp=kline.close_time,
            values={
                "value": round(macd_line, 6),
                "macd": round(macd_line, 6),
                "signal": round(sig, 6),
                "histogram": round(hist, 6),
            },
            is_ready=self.is_ready,
        )

    def reset(self) -> None:
        """Reset MACD state."""
        self._fast_ema.reset()
        self._slow_ema.reset()
        self._signal_val = None
        self._count = 0
        self._last_open_time = None
        self._last_confirmed_signal = None
