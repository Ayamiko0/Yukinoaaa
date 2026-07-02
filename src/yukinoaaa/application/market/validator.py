"""Market Data Validator for integrity and sanity checks."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from yukinoaaa.application.interfaces.logger import ILogger
from yukinoaaa.domain.exceptions import ValidationException
from yukinoaaa.domain.market.models import Kline, Tick


class MarketValidator:
    """Validates real-time ticks and candlesticks to prevent corrupted or anomalous data processing."""

    def __init__(
        self,
        logger: ILogger,
        max_future_drift_seconds: int = 300,
        max_past_drift_seconds: int = 86400,
    ) -> None:
        """Initialize validator with drift thresholds and structured logger."""
        self._logger = logger.bind(module="MarketValidator")
        self._max_future_drift = timedelta(seconds=max_future_drift_seconds)
        self._max_past_drift = timedelta(seconds=max_past_drift_seconds)

    def validate_tick(self, tick: Tick) -> bool:
        """Validate tick data integrity. Returns True if valid, raises or returns False if invalid."""
        try:
            if tick.price <= Decimal("0"):
                raise ValidationException(f"Invalid tick price: {tick.price}")
            if tick.volume < Decimal("0"):
                raise ValidationException(f"Invalid tick volume: {tick.volume}")

            if tick.bid is not None and tick.ask is not None:
                if tick.bid > tick.ask:
                    raise ValidationException(f"Crossed orderbook in tick: bid {tick.bid} > ask {tick.ask}")

            now = datetime.now(timezone.utc)
            tick_time = tick.timestamp.astimezone(timezone.utc)
            if tick_time - now > self._max_future_drift:
                raise ValidationException(f"Tick timestamp too far in future: {tick.timestamp}")
            if now - tick_time > self._max_past_drift:
                raise ValidationException(f"Tick timestamp too old: {tick.timestamp}")

            return True
        except ValidationException as e:
            self._logger.warning("Tick validation failed", symbol=tick.symbol, error=e.message)
            return False
        except Exception as e:
            self._logger.error("Unexpected error during tick validation", symbol=tick.symbol, error=str(e))
            return False

    def validate_kline(self, kline: Kline) -> bool:
        """Validate kline candlestick data integrity."""
        try:
            if kline.high < kline.low:
                raise ValidationException(f"Kline high ({kline.high}) lower than low ({kline.low})")
            if kline.open > kline.high or kline.open < kline.low:
                raise ValidationException(f"Kline open ({kline.open}) out of bounds [{kline.low}, {kline.high}]")
            if kline.close > kline.high or kline.close < kline.low:
                raise ValidationException(f"Kline close ({kline.close}) out of bounds [{kline.low}, {kline.high}]")
            if kline.open_time >= kline.close_time:
                raise ValidationException("Kline open_time must be before close_time")
            return True
        except ValidationException as e:
            self._logger.warning("Kline validation failed", symbol=kline.symbol, error=e.message)
            return False
