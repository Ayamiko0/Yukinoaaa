"""Application notification service bridging domain trading events to Discord alerts."""

from yukinoaaa.application.interfaces.event_bus import IEventBus
from yukinoaaa.application.interfaces.logger import ILogger
from yukinoaaa.application.interfaces.notification import INotificationService
from yukinoaaa.domain.events import DomainEvent
from yukinoaaa.domain.trading.events import (
    OrderFilledEvent,
    PositionClosedEvent,
    PositionOpenedEvent,
    SignalCreatedEvent,
)


class TradingNotificationService:
    """Listens to quantitative trading domain events and dispatches rich Discord alerts."""

    def __init__(
        self,
        notification_service: INotificationService,
        event_bus: IEventBus,
        logger: ILogger,
    ) -> None:
        """Initialize notification service with event bus and Discord adapter."""
        self._notifier = notification_service
        self._event_bus = event_bus
        self._logger = logger.bind(module="TradingNotificationService")
        self._is_running = False

    async def start(self) -> None:
        """Subscribe to trading events and activate notifications."""
        if self._is_running:
            return
        await self._notifier.start()
        await self._event_bus.subscribe("OrderFilled", self._on_order_filled)
        await self._event_bus.subscribe("PositionOpened", self._on_position_opened)
        await self._event_bus.subscribe("PositionClosed", self._on_position_closed)
        await self._event_bus.subscribe("SignalCreated", self._on_signal_created)
        self._is_running = True
        self._logger.info("Trading notification service active and subscribed to EventBus")

    async def stop(self) -> None:
        """Unsubscribe handlers and stop notification adapter."""
        if not self._is_running:
            return
        await self._event_bus.unsubscribe("OrderFilled", self._on_order_filled)
        await self._event_bus.unsubscribe("PositionOpened", self._on_position_opened)
        await self._event_bus.unsubscribe("PositionClosed", self._on_position_closed)
        await self._event_bus.unsubscribe("SignalCreated", self._on_signal_created)
        await self._notifier.stop()
        self._is_running = False
        self._logger.info("Trading notification service cleanly shut down")

    async def _on_order_filled(self, event: DomainEvent) -> None:
        """Handle OrderFilledEvent and send execution embed to Discord."""
        if not isinstance(event, OrderFilledEvent):
            return
        payload = event.payload
        symbol = str(payload.get("symbol", "UNKNOWN"))
        side = str(payload.get("side", "BUY")).upper()
        quantity = str(payload.get("quantity", "0"))
        price = str(payload.get("price", "0"))
        order_id = str(payload.get("order_id", ""))

        color = 0x2ECC71 if side == "BUY" else 0xE74C3C  # Green for BUY, Red for SELL
        fields = [
            {"name": "Symbol", "value": f"`{symbol}`", "inline": True},
            {"name": "Side", "value": f"**{side}**", "inline": True},
            {"name": "Quantity", "value": quantity, "inline": True},
            {"name": "Fill Price", "value": f"${price}", "inline": True},
            {"name": "Order ID", "value": f"`{order_id}`", "inline": False},
        ]
        await self._notifier.send_embed(
            title="⚡ Order Successfully Filled",
            description=f"Automated execution completed for **{symbol}**.",
            color=color,
            fields=fields,
            footer="Yukinoaaa Execution Engine",
        )

    async def _on_position_opened(self, event: DomainEvent) -> None:
        """Handle PositionOpenedEvent alert."""
        if not isinstance(event, PositionOpenedEvent):
            return
        payload = event.payload
        symbol = str(payload.get("symbol", "UNKNOWN"))
        side = str(payload.get("side", "LONG")).upper()
        size = str(payload.get("size", "0"))
        entry_price = str(payload.get("entry_price", "0"))

        fields = [
            {"name": "Symbol", "value": f"`{symbol}`", "inline": True},
            {"name": "Direction", "value": f"**{side}**", "inline": True},
            {"name": "Size", "value": size, "inline": True},
            {"name": "Entry Price", "value": f"${entry_price}", "inline": True},
        ]
        await self._notifier.send_embed(
            title="🚀 Position Opened",
            description=f"New **{side}** position established on **{symbol}**.",
            color=0x3498DB,  # Blue
            fields=fields,
            footer="Yukinoaaa Portfolio Service",
        )

    async def _on_position_closed(self, event: DomainEvent) -> None:
        """Handle PositionClosedEvent alert."""
        if not isinstance(event, PositionClosedEvent):
            return
        payload = event.payload
        symbol = str(payload.get("symbol", "UNKNOWN"))
        side = str(payload.get("side", "LONG")).upper()
        pnl = str(payload.get("realized_pnl", "0"))
        exit_price = str(payload.get("exit_price", "0"))

        is_profit = not pnl.startswith("-")
        color = 0x2ECC71 if is_profit else 0xE74C3C
        icon = "🏆" if is_profit else "🛡️"

        fields = [
            {"name": "Symbol", "value": f"`{symbol}`", "inline": True},
            {"name": "Side", "value": f"**{side}**", "inline": True},
            {"name": "Exit Price", "value": f"${exit_price}", "inline": True},
            {"name": "Realized PnL", "value": f"**${pnl}**", "inline": True},
        ]
        await self._notifier.send_embed(
            title=f"{icon} Position Closed",
            description=f"Position on **{symbol}** settled with realized profit/loss.",
            color=color,
            fields=fields,
            footer="Yukinoaaa Portfolio Service",
        )

    async def _on_signal_created(self, event: DomainEvent) -> None:
        """Handle SignalCreatedEvent alert."""
        if not isinstance(event, SignalCreatedEvent):
            return
        payload = event.payload
        symbol = str(payload.get("symbol", "UNKNOWN"))
        strategy = str(payload.get("strategy_id", "Strategy"))
        direction = str(payload.get("direction", "NEUTRAL")).upper()
        confidence = str(payload.get("confidence", "0"))

        if direction == "NEUTRAL":
            return

        color = 0xF39C12  # Orange for warning/signal
        fields = [
            {"name": "Strategy", "value": f"`{strategy}`", "inline": True},
            {"name": "Instrument", "value": f"`{symbol}`", "inline": True},
            {"name": "Signal", "value": f"**{direction}**", "inline": True},
            {"name": "Confidence", "value": f"{confidence}%", "inline": True},
        ]
        await self._notifier.send_embed(
            title="🎯 Quantitative Strategy Signal",
            description=f"Signal generated by **{strategy}**.",
            color=color,
            fields=fields,
            footer="Yukinoaaa Strategy Engine",
        )
