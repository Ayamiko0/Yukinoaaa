"""Technical Indicator Engine orchestrator."""

from collections import defaultdict
from decimal import Decimal
from typing import Any

from yukinoaaa.application.interfaces.event_bus import IEventBus
from yukinoaaa.application.interfaces.indicator import IIndicator
from yukinoaaa.application.interfaces.logger import ILogger
from yukinoaaa.domain.events import DomainEvent
from yukinoaaa.domain.indicators.events import IndicatorUpdatedEvent
from yukinoaaa.domain.indicators.models import IndicatorValue
from yukinoaaa.domain.market.models import Kline


class IndicatorEngine:
    """Orchestrates indicator calculations and emits IndicatorUpdatedEvent on Kline changes."""

    def __init__(self, event_bus: IEventBus, logger: ILogger) -> None:
        """Initialize indicator registries and subscribe to Event Bus."""
        self._event_bus = event_bus
        self._logger = logger.bind(module="IndicatorEngine")
        # Mapping: (symbol, timeframe) -> list[IIndicator]
        self._indicators: dict[tuple[str, str], list[IIndicator]] = defaultdict(list)
        # Mapping: (symbol, timeframe, indicator_name) -> IndicatorValue
        self._latest_values: dict[tuple[str, str, str], IndicatorValue] = {}
        self._running = False

    async def start(self) -> None:
        """Start listening to KlineReceived events."""
        if self._running:
            return
        self._running = True
        await self._event_bus.subscribe("KlineReceived", self._on_kline_received)
        self._logger.info("Indicator engine started")

    async def stop(self) -> None:
        """Stop listening to events."""
        if not self._running:
            return
        self._running = False
        await self._event_bus.unsubscribe("KlineReceived", self._on_kline_received)
        self._logger.info("Indicator engine stopped")

    def register_indicator(self, symbol: str, timeframe: str, indicator: IIndicator) -> None:
        """Register a technical indicator for a specific symbol and timeframe."""
        key = (symbol.strip().upper(), timeframe.strip().lower())
        if indicator not in self._indicators[key]:
            self._indicators[key].append(indicator)
            self._logger.debug("Registered indicator", symbol=key[0], timeframe=key[1], name=indicator.name)

    def get_latest_value(self, symbol: str, timeframe: str, indicator_name: str) -> IndicatorValue | None:
        """Retrieve the latest computed IndicatorValue."""
        key = (symbol.strip().upper(), timeframe.strip().lower(), indicator_name)
        return self._latest_values.get(key)

    def get_all_latest_values(self, symbol: str, timeframe: str) -> dict[str, IndicatorValue]:
        """Retrieve all current indicator values for a symbol and timeframe."""
        sym = symbol.strip().upper()
        tf = timeframe.strip().lower()
        return {
            k[2]: v
            for k, v in self._latest_values.items()
            if k[0] == sym and k[1] == tf
        }

    async def _on_kline_received(self, event: DomainEvent) -> None:
        """Event bus handler triggered when a new Kline is updated or closed."""
        if not self._running:
            return

        payload: dict[str, Any] = event.payload
        sym = str(payload.get("symbol", "")).strip().upper()
        tf = str(payload.get("timeframe", "")).strip().lower()

        key = (sym, tf)
        indicators = self._indicators.get(key, [])
        if not indicators:
            return

        # Reconstruct Kline from payload or if kline object was embedded
        kline_obj = payload.get("kline_obj")
        if isinstance(kline_obj, Kline):
            kline = kline_obj
        else:
            # Fallback basic reconstruction if needed
            close_val = Decimal(str(payload.get("close", "100.0")))
            kline = Kline(
                symbol=sym,
                timeframe=tf,
                open_time=event.timestamp,
                close_time=event.timestamp,
                open=close_val,
                high=close_val,
                low=close_val,
                close=close_val,
            )

        for ind in indicators:
            try:
                res = ind.update(kline)
                self._latest_values[(sym, tf, ind.name)] = res

                if res.is_ready:
                    await self._event_bus.publish(
                        IndicatorUpdatedEvent(
                            event_type="IndicatorUpdated",
                            payload={
                                "symbol": sym,
                                "timeframe": tf,
                                "indicator_name": ind.name,
                                "values": {k: str(v) for k, v in res.values.items()},
                                "is_ready": res.is_ready,
                            },
                        )
                    )
            except Exception as e:
                self._logger.error("Error calculating indicator", name=ind.name, symbol=sym, error=str(e))
