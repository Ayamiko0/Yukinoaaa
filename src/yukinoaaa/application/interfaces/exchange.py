"""Exchange Adapter interface contract."""

from abc import ABC, abstractmethod
from collections.abc import Callable, Coroutine
from typing import Any

from yukinoaaa.domain.market.models import Kline, OrderBook, Tick

# Type alias for async tick callback handler
TickCallback = Callable[[Tick], Coroutine[Any, Any, None]]


class IExchangeAdapter(ABC):
    """Abstract interface for interacting with cryptocurrency or forex exchanges."""

    @property
    @abstractmethod
    def exchange_id(self) -> str:
        """Return unique exchange identifier string (e.g., 'binance', 'bybit', 'mt5', 'mock')."""
        ...

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection or initialize API sessions with the exchange."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Cleanly terminate connections and release exchange resources."""
        ...

    @abstractmethod
    async def get_ticker(self, symbol: str) -> Tick:
        """Fetch the latest price ticker for a symbol via REST/RPC."""
        ...

    @abstractmethod
    async def get_klines(self, symbol: str, timeframe: str, limit: int = 100) -> list[Kline]:
        """Fetch historical candlestick bars for a symbol."""
        ...

    @abstractmethod
    async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderBook:
        """Fetch current order book depth for a symbol."""
        ...

    @abstractmethod
    async def subscribe_ticks(self, symbols: list[str], callback: TickCallback) -> None:
        """Subscribe to real-time tick streaming for specified symbols."""
        ...

    @abstractmethod
    async def unsubscribe_ticks(self, symbols: list[str]) -> None:
        """Unsubscribe from real-time tick streaming for specified symbols."""
        ...

    @abstractmethod
    def is_connected(self) -> bool:
        """Check whether the exchange adapter is actively connected."""
        ...
