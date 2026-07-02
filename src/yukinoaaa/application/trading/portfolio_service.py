"""Portfolio Service orchestrator for real-time equity and position tracking."""

from decimal import Decimal
from typing import Any

from yukinoaaa.application.interfaces.cache import ICache
from yukinoaaa.application.interfaces.event_bus import IEventBus
from yukinoaaa.application.interfaces.logger import ILogger
from yukinoaaa.domain.events import DomainEvent
from yukinoaaa.domain.trading.events import PositionClosedEvent, PositionOpenedEvent
from yukinoaaa.domain.trading.models import Portfolio, Position


class PortfolioService:
    """Manages trading account portfolio and listens to real-time tick updates."""

    def __init__(self, cache: ICache, event_bus: IEventBus, logger: ILogger, default_account_id: str = "default_acc") -> None:
        """Initialize portfolio service with dependencies and cache fallback."""
        self._cache = cache
        self._event_bus = event_bus
        self._logger = logger.bind(module="PortfolioService", account_id=default_account_id)
        self._portfolio = Portfolio(account_id=default_account_id, available_balance=Decimal("100000.00"))
        self._running = False

    @property
    def portfolio(self) -> Portfolio:
        """Return current in-memory Portfolio aggregate."""
        return self._portfolio

    async def start(self) -> None:
        """Start listening to real-time market ticks."""
        if self._running:
            return
        self._running = True
        await self._event_bus.subscribe("TickReceived", self._on_tick_received)
        self._logger.info("Portfolio service started")

    async def stop(self) -> None:
        """Stop listening to tick events."""
        if not self._running:
            return
        self._running = False
        await self._event_bus.unsubscribe("TickReceived", self._on_tick_received)
        self._logger.info("Portfolio service stopped")

    async def open_position(self, pos: Position, required_margin: Decimal) -> None:
        """Open position in portfolio and publish PositionOpenedEvent."""
        self._portfolio.open_position(pos, required_margin)
        self._logger.info("Opened position", symbol=pos.symbol, side=pos.side.value, quantity=str(pos.quantity))

        await self._event_bus.publish(
            PositionOpenedEvent(
                event_type="PositionOpened",
                payload={
                    "account_id": self._portfolio.account_id,
                    "position_id": pos.id,
                    "symbol": pos.symbol,
                    "side": pos.side.value,
                    "entry_price": str(pos.entry_price),
                    "quantity": str(pos.quantity),
                },
            )
        )

    async def close_position(self, symbol: str, close_price: Decimal) -> Position:
        """Close position in portfolio and publish PositionClosedEvent."""
        pos = self._portfolio.close_position(symbol, close_price)
        self._logger.info(
            "Closed position", symbol=pos.symbol, side=pos.side.value, realized_pnl=str(pos.realized_pnl)
        )

        await self._event_bus.publish(
            PositionClosedEvent(
                event_type="PositionClosed",
                payload={
                    "account_id": self._portfolio.account_id,
                    "position_id": pos.id,
                    "symbol": pos.symbol,
                    "close_price": str(close_price),
                    "realized_pnl": str(pos.realized_pnl),
                },
            )
        )
        return pos

    async def _on_tick_received(self, event: DomainEvent) -> None:
        """Event handler triggered when a real-time price update arrives."""
        if not self._running:
            return

        payload: dict[str, Any] = event.payload
        sym = str(payload.get("symbol", "")).strip().upper()
        price_str = payload.get("price")
        if not sym or not price_str:
            return

        try:
            price = Decimal(str(price_str))
            pnl = self._portfolio.update_position_price(sym, price)
            if pnl is not None:
                self._logger.debug("Updated position mark price", symbol=sym, mark_price=str(price), pnl=str(pnl))
        except Exception as e:
            self._logger.error("Error updating position price on tick", symbol=sym, error=str(e))
