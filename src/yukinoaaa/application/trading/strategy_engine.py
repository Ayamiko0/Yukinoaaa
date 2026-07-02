"""Strategy Engine orchestrator evaluating quantitative strategy plugins."""

from collections import defaultdict
from typing import Any
from yukinoaaa.application.interfaces.event_bus import IEventBus
from yukinoaaa.application.interfaces.logger import ILogger
from yukinoaaa.application.interfaces.strategy import IStrategy
from yukinoaaa.domain.events import DomainEvent
from yukinoaaa.domain.trading.events import SignalCreatedEvent
from yukinoaaa.domain.trading.models import TradeSignal


class StrategyEngine:
    """Orchestrates strategy evaluation and emits SignalCreatedEvent upon setup confirmation."""

    def __init__(self, event_bus: IEventBus, logger: ILogger) -> None:
        """Initialize strategy registries and subscribe to Event Bus."""
        self._event_bus = event_bus
        self._logger = logger.bind(module="StrategyEngine")
        # Mapping: (symbol, timeframe) -> list[IStrategy]
        self._strategies: dict[tuple[str, str], list[IStrategy]] = defaultdict(list)
        self._running = False

    async def start(self) -> None:
        """Start listening to IndicatorUpdated and MarketSnapshotUpdated events."""
        if self._running:
            return
        self._running = True
        await self._event_bus.subscribe("IndicatorUpdated", self._on_indicator_updated)
        self._logger.info("Strategy engine started")

    async def stop(self) -> None:
        """Stop listening to events."""
        if not self._running:
            return
        self._running = False
        await self._event_bus.unsubscribe("IndicatorUpdated", self._on_indicator_updated)
        self._logger.info("Strategy engine stopped")

    def register_strategy(self, strategy: IStrategy) -> None:
        """Register a strategy plugin."""
        key = (strategy.symbol.strip().upper(), strategy.timeframe.strip().lower())
        if strategy not in self._strategies[key]:
            self._strategies[key].append(strategy)
            self._logger.info("Registered strategy plugin", name=strategy.name, symbol=key[0], timeframe=key[1])

    async def _on_indicator_updated(self, event: DomainEvent) -> None:
        """Event bus handler triggered when a technical indicator is updated."""
        if not self._running:
            return

        payload: dict[str, Any] = event.payload
        sym = str(payload.get("symbol", "")).strip().upper()
        tf = str(payload.get("timeframe", "")).strip().lower()
        ind_name = str(payload.get("indicator_name", ""))
        values: dict[str, Any] = payload.get("values", {})
        is_ready = bool(payload.get("is_ready", True))

        if not is_ready:
            return

        key = (sym, tf)
        strategies = self._strategies.get(key, [])
        if not strategies:
            return

        for strat in strategies:
            try:
                signal: TradeSignal | None = strat.on_indicator_updated(ind_name, values)
                if signal is not None:
                    await self._emit_signal(signal)
            except Exception as e:
                self._logger.error("Error evaluating strategy", strategy=strat.name, symbol=sym, error=str(e))

    async def _emit_signal(self, signal: TradeSignal) -> None:
        """Publish SignalCreatedEvent over Event Bus."""
        self._logger.info(
            "Trade signal generated",
            strategy=signal.strategy_name,
            symbol=signal.symbol,
            side=signal.side.value,
            confidence=signal.confidence,
        )
        await self._event_bus.publish(
            SignalCreatedEvent(
                event_type="SignalCreated",
                payload={
                    "signal_id": signal.signal_id,
                    "symbol": signal.symbol,
                    "timeframe": signal.timeframe,
                    "side": signal.side.value,
                    "strategy_name": signal.strategy_name,
                    "confidence": str(signal.confidence),
                    "target_price": str(signal.target_price) if signal.target_price else None,
                    "stop_loss": str(signal.stop_loss) if signal.stop_loss else None,
                },
            )
        )
