"""Order Router dispatching orders to target execution adapters."""

from typing import Any

from yukinoaaa.application.interfaces.event_bus import IEventBus
from yukinoaaa.application.interfaces.execution import IExecutionAdapter
from yukinoaaa.application.interfaces.logger import ILogger
from yukinoaaa.application.trading.portfolio_service import PortfolioService
from yukinoaaa.domain.events import DomainEvent
from yukinoaaa.domain.execution.events import ExecutionReportReceivedEvent


class OrderRouter:
    """Routes OrderCreatedEvent to appropriate execution adapter and publishes execution reports."""

    def __init__(
        self, portfolio_service: PortfolioService, event_bus: IEventBus, logger: ILogger
    ) -> None:
        """Initialize router with portfolio service, event bus, and adapter registry."""
        self._portfolio_service = portfolio_service
        self._event_bus = event_bus
        self._logger = logger.bind(module="OrderRouter")
        self._adapters: dict[str, IExecutionAdapter] = {}
        self._default_adapter: str = "MOCK"
        self._running = False

    def register_adapter(
        self, name: str, adapter: IExecutionAdapter, is_default: bool = False
    ) -> None:
        """Register an execution adapter under a unique identifier."""
        name_up = name.upper()
        self._adapters[name_up] = adapter
        if is_default or not self._adapters:
            self._default_adapter = name_up
        self._logger.info("Registered execution adapter", name=name_up, is_default=is_default)

    async def start(self) -> None:
        """Subscribe to OrderCreatedEvent."""
        if self._running:
            return
        self._running = True
        await self._event_bus.subscribe("OrderCreated", self._on_order_created)
        self._logger.info("Order router started")

    async def stop(self) -> None:
        """Unsubscribe from events."""
        if not self._running:
            return
        self._running = False
        await self._event_bus.unsubscribe("OrderCreated", self._on_order_created)
        self._logger.info("Order router stopped")

    async def _on_order_created(self, event: DomainEvent) -> None:
        """Handle new order, select adapter, submit order, and publish ExecutionReport."""
        if not self._running:
            return

        payload: dict[str, Any] = event.payload
        order_id = str(payload.get("order_id", ""))
        if not order_id:
            return

        order = self._portfolio_service.portfolio.orders.get(order_id)
        if not order:
            self._logger.error("Order not found in portfolio for routing", order_id=order_id)
            return

        adapter_name = str(payload.get("adapter", self._default_adapter)).upper()
        adapter = self._adapters.get(adapter_name) or self._adapters.get(self._default_adapter)
        if not adapter:
            self._logger.error("No execution adapter available to process order", order_id=order_id)
            return

        try:
            report = await adapter.submit_order(order)
            self._logger.info(
                "Order submitted to adapter", order_id=order.id, status=report.status.value
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
                        "last_price": str(report.last_price) if report.last_price else None,
                        "average_price": str(report.average_price)
                        if report.average_price
                        else None,
                        "fee": str(report.fee),
                        "reason": report.reason,
                    },
                )
            )
        except Exception as e:
            self._logger.error("Error submitting order to adapter", order_id=order_id, error=str(e))
