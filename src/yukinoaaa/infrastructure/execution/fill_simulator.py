"""Fill Simulator matching pending limit/stop orders against real-time tick prices."""

from decimal import Decimal
from typing import Any

from yukinoaaa.application.interfaces.event_bus import IEventBus
from yukinoaaa.application.interfaces.logger import ILogger
from yukinoaaa.domain.events import DomainEvent
from yukinoaaa.domain.execution.events import ExecutionReportReceivedEvent
from yukinoaaa.domain.execution.models import ExecutionReport, ExecutionState
from yukinoaaa.domain.trading.models import Order, OrderSide, OrderType


class FillSimulator:
    """Monitors real-time tick events and simulates execution of pending limit and stop orders."""

    def __init__(
        self,
        event_bus: IEventBus,
        logger: ILogger,
        slippage_rate: Decimal = Decimal("0.0005"),
        fee_rate: Decimal = Decimal("0.0010"),
    ) -> None:
        """Initialize simulator with event bus and fee schedules."""
        self._event_bus = event_bus
        self._logger = logger.bind(module="FillSimulator")
        self._pending_orders: dict[str, Order] = {}
        self._slippage = slippage_rate
        self._fee_rate = fee_rate
        self._running = False

    @property
    def pending_orders(self) -> dict[str, Order]:
        """Return dict of currently monitored pending orders."""
        return self._pending_orders

    def add_pending_order(self, order: Order) -> None:
        """Register a pending order for price monitoring."""
        self._pending_orders[order.id] = order
        self._logger.info(
            "Queued order for fill simulation", order_id=order.id, type=order.order_type.value
        )

    def remove_pending_order(self, order_id: str) -> None:
        """Remove a pending order from monitoring."""
        self._pending_orders.pop(order_id, None)

    async def start(self) -> None:
        """Subscribe to real-time TickReceived events."""
        if self._running:
            return
        self._running = True
        await self._event_bus.subscribe("TickReceived", self._on_tick_received)
        self._logger.info("Fill simulator started")

    async def stop(self) -> None:
        """Unsubscribe from events."""
        if not self._running:
            return
        self._running = False
        await self._event_bus.unsubscribe("TickReceived", self._on_tick_received)
        self._logger.info("Fill simulator stopped")

    async def _on_tick_received(self, event: DomainEvent) -> None:
        """Evaluate pending orders against incoming price tick."""
        if not self._running or not self._pending_orders:
            return

        payload: dict[str, Any] = event.payload
        sym = str(payload.get("symbol", "")).strip().upper()
        price_str = payload.get("price")
        if not sym or not price_str:
            return

        try:
            tick_price = Decimal(str(price_str))
            triggered_ids: list[str] = []

            for order_id, order in list(self._pending_orders.items()):
                if order.symbol != sym:
                    continue

                target_price = order.price
                if not target_price:
                    continue

                is_triggered = (
                    order.order_type == OrderType.LIMIT
                    and (
                        (order.side == OrderSide.BUY and tick_price <= target_price)
                        or (order.side == OrderSide.SELL and tick_price >= target_price)
                    )
                ) or (
                    order.order_type in (OrderType.STOP_LOSS, OrderType.TAKE_PROFIT)
                    and (
                        (order.side == OrderSide.BUY and tick_price >= target_price)
                        or (order.side == OrderSide.SELL and tick_price <= target_price)
                    )
                )

                if is_triggered:
                    triggered_ids.append(order_id)
                    await self._execute_order(order, tick_price)

            for tid in triggered_ids:
                self._pending_orders.pop(tid, None)

        except Exception as e:
            self._logger.error("Error evaluating fill simulator on tick", symbol=sym, error=str(e))

    async def _execute_order(self, order: Order, tick_price: Decimal) -> None:
        """Simulate fill execution and publish report."""
        if order.side == OrderSide.BUY:
            fill_price = tick_price * (Decimal("1.0") + self._slippage)
        else:
            fill_price = tick_price * (Decimal("1.0") - self._slippage)
        fill_price = fill_price.quantize(Decimal("0.000001"))

        fee = (order.quantity * fill_price * self._fee_rate).quantize(Decimal("0.000001"))

        self._logger.info(
            "Simulated order fill triggered", order_id=order.id, price=str(fill_price)
        )

        report = ExecutionReport(
            order_id=order.id,
            symbol=order.symbol,
            status=ExecutionState.FILLED,
            filled_quantity=order.quantity,
            remaining_quantity=Decimal("0.0"),
            last_price=fill_price,
            average_price=fill_price,
            fee=fee,
        )

        await self._event_bus.publish(
            ExecutionReportReceivedEvent(
                event_type="ExecutionReportReceived",
                payload={
                    "report_id": report.report_id,
                    "order_id": report.order_id,
                    "symbol": report.symbol,
                    "status": report.status.value,
                    "filled_quantity": str(report.filled_quantity),
                    "remaining_quantity": str(report.remaining_quantity),
                    "last_price": str(report.last_price),
                    "average_price": str(report.average_price),
                    "fee": str(report.fee),
                },
            )
        )
