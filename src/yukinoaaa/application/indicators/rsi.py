"""Relative Strength Index (RSI) implementation with Wilder's smoothing."""

from decimal import Decimal
from yukinoaaa.application.interfaces.indicator import IIndicator
from yukinoaaa.domain.indicators.models import IndicatorValue
from yukinoaaa.domain.market.models import Kline


class RSI(IIndicator):
    """Relative Strength Index using Wilder's smoothing technique."""

    def __init__(self, period: int = 14) -> None:
        """Initialize Wilder's gain/loss tracking variables."""
        if period <= 0:
            raise ValueError("RSI period must be positive")
        self._period = period
        self._count = 0
        self._prev_close: Decimal | None = None
        self._avg_gain = Decimal("0")
        self._avg_loss = Decimal("0")
        self._last_open_time = None
        self._last_confirmed_close: Decimal | None = None
        self._last_confirmed_gain = Decimal("0")
        self._last_confirmed_loss = Decimal("0")

    @property
    def name(self) -> str:
        return f"RSI_{self._period}"

    @property
    def period(self) -> int:
        return self._period

    @property
    def is_ready(self) -> bool:
        return self._count >= self._period + 1

    def update(self, kline: Kline) -> IndicatorValue:
        """Update RSI with new closing price."""
        close_price = kline.close

        is_new_bar = self._last_open_time != kline.open_time
        if is_new_bar:
            if self._prev_close is not None:
                self._last_confirmed_close = self._prev_close
                self._last_confirmed_gain = self._avg_gain
                self._last_confirmed_loss = self._avg_loss
            self._count += 1
            self._last_open_time = kline.open_time

        prev_c = self._last_confirmed_close
        if prev_c is None:
            self._prev_close = close_price
            return self._build_result(kline, Decimal("50.0"))

        change = close_price - prev_c
        gain = max(change, Decimal("0"))
        loss = max(-change, Decimal("0"))

        if self._count <= self._period + 1:
            # Simple average during warmup
            if is_new_bar:
                self._avg_gain = (self._last_confirmed_gain * Decimal(str(self._count - 2)) + gain) / Decimal(
                    str(self._count - 1)
                ) if self._count > 1 else gain
                self._avg_loss = (self._last_confirmed_loss * Decimal(str(self._count - 2)) + loss) / Decimal(
                    str(self._count - 1)
                ) if self._count > 1 else loss
            else:
                self._avg_gain = (self._last_confirmed_gain * Decimal(str(self._count - 2)) + gain) / Decimal(
                    str(self._count - 1)
                ) if self._count > 1 else gain
                self._avg_loss = (self._last_confirmed_loss * Decimal(str(self._count - 2)) + loss) / Decimal(
                    str(self._count - 1)
                ) if self._count > 1 else loss
        else:
            # Wilder's smoothing
            self._avg_gain = (self._last_confirmed_gain * Decimal(str(self._period - 1)) + gain) / Decimal(str(self._period))
            self._avg_loss = (self._last_confirmed_loss * Decimal(str(self._period - 1)) + loss) / Decimal(str(self._period))

        self._prev_close = close_price

        if self._avg_loss == Decimal("0"):
            rsi_val = Decimal("100.0") if self._avg_gain > Decimal("0") else Decimal("50.0")
        else:
            rs = self._avg_gain / self._avg_loss
            rsi_val = Decimal("100.0") - (Decimal("100.0") / (Decimal("1.0") + rs))

        return self._build_result(kline, rsi_val)

    def _build_result(self, kline: Kline, val: Decimal) -> IndicatorValue:
        return IndicatorValue(
            name=self.name,
            symbol=kline.symbol,
            timeframe=kline.timeframe,
            timestamp=kline.close_time,
            values={"value": round(val, 4), "rsi": round(val, 4)},
            is_ready=self.is_ready,
        )

    def reset(self) -> None:
        """Reset RSI state."""
        self._count = 0
        self._prev_close = None
        self._avg_gain = Decimal("0")
        self._avg_loss = Decimal("0")
        self._last_open_time = None
        self._last_confirmed_close = None
        self._last_confirmed_gain = Decimal("0")
        self._last_confirmed_loss = Decimal("0")
