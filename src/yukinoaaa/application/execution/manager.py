"""Order Manager central state synchronization engine."""

from decimal import Decimal
from typing import Any
from yukinoaaa.application.interfaces.event_bus import IEventBus
from yukinoaaa.application.interfaces.logger import ILogger
from yukinoaaa.application.trading.portfolio_service import PortfolioService
from yukinoaaa.domain.events import DomainEvent
from yukinoaaa.domain.execution.events import OrderExecutionCompletedEvent, OrderPartiallyFilledEvent
from yukinoaaa.domain.execution.models import ExecutionState
from yukinoaaa.domain.trading.events import OrderFilledEvent
from yukinoaaa.domain.trading.models import Order, OrderSide, OrderStatus, Position, PositionSide


class OrderManager:
    """Tracks active order lifecycle, synchronizes state, and registers filled positions."""

    def __init__(self, portfolio_service: PortfolioService, event_bus: IEventBus, logger: ILogger) -> None:
        """Initialize order manager with portfolio service and event bus."""
        self._portfolio_service = portfolio_service
        self._event_bus = event_bus
        self._logger = logger.bind(module="OrderManager")
        self._active_orders: dict[str, Order] = {}
        self._running = False

    def get_active_orders(self, symbol: str | None = None) -> list[Order]:
        """Return list of active orders, optionally filtered by symbol."""
        if symbol:
            sym_up = symbol.upper()
            return [o for o in self._active_orders.values() if o.symbol == sym_up]
        return list(self._active_orders.values())

    async def start(self) -> None:
        """Subscribe to ExecutionReportReceived events."""
        if self._running:
            return
        self._running = True
        await self._event_bus.subscribe("ExecutionReportReceived", self._on_execution_report)
        self._logger.info("Order manager started")

    async def stop(self) -> None:
        """Unsubscribe from events."""
        if not self._running:
            return
        self._running = False
        await self._event_bus.unsubscribe("ExecutionReportReceived", self._on_execution_report)
        self._logger.info("Order manager stopped")

    async def _on_execution_report(self, event: DomainEvent) -> None:
        """Handle execution report, update order state, and emit terminal completion events."""
        if not self._running:
            return

        payload: dict[str, Any] = event.payload
        order_id = str(payload.get("order_id", ""))
        status_str = str(payload.get("status", ""))
        filled_qty_str = payload.get("filled_quantity", "0.0")
        avg_price_str = payload.get("average_price")

        if not order_id or not status_str:
            return

        port = self._portfolio_service.portfolio
        order = self._active_orders.get(order_id) or port.orders.get(order_id)
        if not order:
            self._logger.warning("Received report for unknown order", order_id=order_id, status=status_str)
            return

        # Track active orders
        if order_id not in self._active_orders and status_str in (
            ExecutionState.SUBMITTED.value,
            ExecutionState.PARTIAL_FILLED.value,
        ):
            self._active_orders[order_id] = order

        try:
            # Synchronize state
            try:
                order.status = OrderStatus(status_str)
            except ValueError:
                pass

            filled_qty = Decimal(str(filled_qty_str))
            order.filled_quantity = filled_qty
            if avg_price_str:
                order.average_fill_price = Decimal(str(avg_price_str))

            self._logger.info("Updated order state", order_id=order.id, symbol=order.symbol, status=status_str)

            # Emit partial fill event
            if status_str == ExecutionState.PARTIAL_FILLED.value:
                await self._event_bus.publish(
                    OrderPartiallyFilledEvent(
                        event_type="OrderPartiallyFilled",
                        payload={"order_id": order.id, "symbol": order.symbol, "filled_quantity": str(filled_qty)},
                    )
                )

            # Handle terminal states
            elif status_str == ExecutionState.FILLED.value:
                self._active_orders.pop(order_id, None)
                fill_price = order.average_fill_price or order.price or Decimal("100.0")
                pos_side = PositionSide.LONG if order.side == OrderSide.BUY else PositionSide.SHORT

                pos = Position(
                    symbol=order.symbol,
                    side=pos_side,
                    entry_price=fill_price,
                    mark_price=fill_price,
                    quantity=order.filled_quantity,
                )
                await self._portfolio_service.open_position(pos, required_margin=Decimal("0.0"))

                await self._event_bus.publish(
                    OrderFilledEvent(
                        event_type="OrderFilled",
                        payload={
                            "order_id": order.id,
                            "symbol": order.symbol,
                            "filled_quantity": str(order.filled_quantity),
                            "average_price": str(fill_price),
                        },
                    )
                )
                await self._event_bus.publish(
                    OrderExecutionCompletedEvent(
                        event_type="OrderExecutionCompleted",
                        payload={"order_id": order.id, "symbol": order.symbol, "status": status_str},
                    )
                )

            elif status_str in (
                ExecutionState.CANCELLED.value,
                ExecutionState.REJECTED.value,
                ExecutionState.FAILED.value,
            ):
                self._active_orders.pop(order_id, None)
                await self._event_bus.publish(
                    OrderExecutionCompletedEvent(
                        event_type="OrderExecutionCompleted",
                        payload={"order_id": order.id, "symbol": order.symbol, "status": status_str},
                    )
                )
        except Exception as e:
            self._logger.error("Error processing execution report", order_id=order_id, error=str(e))
