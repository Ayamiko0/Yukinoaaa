"""Market Data Normalizer and Deduplication engine."""

from yukinoaaa.application.interfaces.logger import ILogger
from yukinoaaa.domain.market.models import Tick


class MarketNormalizer:
    """Normalizes raw ticks into canonical format and prevents duplicate event processing."""

    def __init__(self, logger: ILogger) -> None:
        """Initialize normalizer with last seen tick state for deduplication."""
        self._logger = logger.bind(module="MarketNormalizer")
        # Track last processed tick per (exchange, symbol)
        self._last_ticks: dict[tuple[str, str], Tick] = {}

    def normalize_and_deduplicate(self, tick: Tick) -> Tick | None:
        """Ensure canonical formatting and discard duplicate ticks.

        Returns normalized Tick or None if duplicate.
        """
        key = (tick.exchange.lower(), tick.symbol.upper())

        # Check for deduplication
        last_tick = self._last_ticks.get(key)
        if (
            last_tick is not None
            and last_tick.timestamp == tick.timestamp
            and last_tick.price == tick.price
            and last_tick.volume == tick.volume
        ):
            self._logger.debug(
                "Duplicate tick discarded", symbol=tick.symbol, exchange=tick.exchange
            )
            return None

        # Create normalized copy if symbol wasn't uppercase
        normalized_symbol = tick.symbol.strip().upper()
        if normalized_symbol != tick.symbol:
            tick = Tick(
                symbol=normalized_symbol,
                price=tick.price,
                volume=tick.volume,
                bid=tick.bid,
                ask=tick.ask,
                timestamp=tick.timestamp,
                exchange=tick.exchange,
            )

        self._last_ticks[key] = tick
        return tick

    def reset_state(self, symbol: str | None = None, exchange: str | None = None) -> None:
        """Reset deduplication memory cache (useful for tests or reconnection)."""
        if symbol is None and exchange is None:
            self._last_ticks.clear()
        else:
            to_remove = [
                k
                for k in self._last_ticks
                if (exchange is None or k[0] == exchange.lower())
                and (symbol is None or k[1] == symbol.upper())
            ]
            for k in to_remove:
                self._last_ticks.pop(k, None)
