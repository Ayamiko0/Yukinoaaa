"""Abstract interface contract for trading execution adapters."""

from abc import ABC, abstractmethod

from yukinoaaa.domain.execution.models import ExecutionReport
from yukinoaaa.domain.trading.models import Order


class IExecutionAdapter(ABC):
    """Abstract base class for order routing and execution adapters."""

    @abstractmethod
    async def submit_order(self, order: Order) -> ExecutionReport:
        """Submit a trading order to exchange or simulation simulator."""
        ...

    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> ExecutionReport:
        """Request cancellation of an active order."""
        ...

    @abstractmethod
    async def get_order_status(self, order_id: str, symbol: str) -> ExecutionReport | None:
        """Retrieve latest execution report for an order."""
        ...
