"""Mock Execution Adapter providing realistic fill simulation for paper trading."""

from decimal import Decimal
from typing import TYPE_CHECKING
from yukinoaaa.application.interfaces.execution import IExecutionAdapter
from yukinoaaa.application.trading.portfolio_service import PortfolioService
from yukinoaaa.domain.execution.models import ExecutionReport, ExecutionState
from yukinoaaa.domain.trading.models import Order, OrderSide, OrderType

if TYPE_CHECKING:
    from yukinoaaa.infrastructure.execution.fill_simulator import FillSimulator


class MockExecutionAdapter(IExecutionAdapter):
    """Simulates instant execution for market orders and queues limit/stop orders."""

    def __init__(
        self,
        portfolio_service: PortfolioService,
        fill_simulator: "FillSimulator | None" = None,
        slippage_rate: Decimal = Decimal("0.0005"),
        fee_rate: Decimal = Decimal("0.0010"),
    ) -> None:
        """Initialize mock adapter with slippage and commission fee rates."""
        self._portfolio_service = portfolio_service
        self._simulator = fill_simulator
        self._slippage = slippage_rate
        self._fee_rate = fee_rate

    async def submit_order(self, order: Order) -> ExecutionReport:
        """Process order submission, filling Market orders immediately with slippage and fee."""
        if order.order_type == OrderType.MARKET:
            base_price = order.price or Decimal("100.0")
            if order.symbol in self._portfolio_service.portfolio.positions:
                base_price = self._portfolio_service.portfolio.positions[order.symbol].mark_price

            # Apply slippage
            if order.side == OrderSide.BUY:
                fill_price = base_price * (Decimal("1.0") + self._slippage)
            else:
                fill_price = base_price * (Decimal("1.0") - self._slippage)
            fill_price = fill_price.quantize(Decimal("0.000001"))

            fee = (order.quantity * fill_price * self._fee_rate).quantize(Decimal("0.000001"))

            return ExecutionReport(
                order_id=order.id,
                symbol=order.symbol,
                status=ExecutionState.FILLED,
                filled_quantity=order.quantity,
                remaining_quantity=Decimal("0.0"),
                last_price=fill_price,
                average_price=fill_price,
                fee=fee,
            )

        # For Limit and Stop orders, queue in simulator
        if self._simulator:
            self._simulator.add_pending_order(order)

        return ExecutionReport(
            order_id=order.id,
            symbol=order.symbol,
            status=ExecutionState.SUBMITTED,
            filled_quantity=Decimal("0.0"),
            remaining_quantity=order.quantity,
        )

    async def cancel_order(self, order_id: str, symbol: str) -> ExecutionReport:
        """Cancel pending order from simulator queue."""
        if self._simulator:
            self._simulator.remove_pending_order(order_id)
        return ExecutionReport(order_id=order_id, symbol=symbol, status=ExecutionState.CANCELLED)

    async def get_order_status(self, order_id: str, symbol: str) -> ExecutionReport | None:
        """Return status query report."""
        if self._simulator and order_id in self._simulator.pending_orders:
            return ExecutionReport(order_id=order_id, symbol=symbol, status=ExecutionState.SUBMITTED)
        return None
