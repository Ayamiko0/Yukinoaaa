"""Average True Range (ATR) indicator implementation."""

from decimal import Decimal
from typing import TYPE_CHECKING

from yukinoaaa.application.interfaces.indicator import IIndicator
from yukinoaaa.domain.indicators.models import IndicatorValue
from yukinoaaa.domain.market.models import Kline

if TYPE_CHECKING:
    from datetime import datetime


class ATR(IIndicator):
    """Average True Range using Wilder's True Range smoothing."""

    def __init__(self, period: int = 14) -> None:
        """Initialize Wilder smoothing alpha and True Range state."""
        if period <= 0:
            raise ValueError("ATR period must be positive")
        self._period = period
        self._count = 0
        self._prev_close: Decimal | None = None
        self._atr_val: Decimal | None = None
        self._warmup_sum = Decimal("0")
        self._last_open_time: datetime | None = None
        self._last_confirmed_close: Decimal | None = None
        self._last_confirmed_atr: Decimal | None = None

    @property
    def name(self) -> str:
        return f"ATR_{self._period}"

    @property
    def period(self) -> int:
        return self._period

    @property
    def is_ready(self) -> bool:
        return self._count >= self._period

    def update(self, kline: Kline) -> IndicatorValue:
        """Update ATR with high, low, and closing prices."""
        is_new_bar = self._last_open_time != kline.open_time
        if is_new_bar:
            if self._prev_close is not None:
                self._last_confirmed_close = self._prev_close
                if self._atr_val is not None:
                    self._last_confirmed_atr = self._atr_val
            self._count += 1
            self._last_open_time = kline.open_time

        prev_c = self._last_confirmed_close
        if prev_c is None:
            tr = kline.high - kline.low
        else:
            tr = max(
                kline.high - kline.low,
                abs(kline.high - prev_c),
                abs(kline.low - prev_c),
            )

        if self._count <= self._period:
            if is_new_bar:
                self._warmup_sum += tr
            val = self._warmup_sum / Decimal(str(self._count))
            self._atr_val = val
        else:
            prev_atr = self._last_confirmed_atr if self._last_confirmed_atr is not None else tr
            val = (prev_atr * Decimal(str(self._period - 1)) + tr) / Decimal(str(self._period))
            self._atr_val = val

        self._prev_close = kline.close

        return IndicatorValue(
            name=self.name,
            symbol=kline.symbol,
            timeframe=kline.timeframe,
            timestamp=kline.close_time,
            values={"value": round(val, 6), "atr": round(val, 6), "true_range": round(tr, 6)},
            is_ready=self.is_ready,
        )

    def reset(self) -> None:
        """Reset ATR state."""
        self._count = 0
        self._prev_close = None
        self._atr_val = None
        self._warmup_sum = Decimal("0")
        self._last_open_time = None
        self._last_confirmed_close = None
        self._last_confirmed_atr = None
