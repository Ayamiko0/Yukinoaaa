"""Mock / Simulated Exchange Adapter for testing and 24/7 standalone paper trading."""

import asyncio
import contextlib
import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from yukinoaaa.application.interfaces.exchange import IExchangeAdapter, TickCallback
from yukinoaaa.application.interfaces.logger import ILogger
from yukinoaaa.domain.exceptions import InfrastructureException
from yukinoaaa.domain.market.models import Kline, OrderBook, OrderBookEntry, Tick


class MockExchangeAdapter(IExchangeAdapter):
    """Simulates real-time market data (Crypto, Forex, Metals) using Brownian motion."""

    def __init__(
        self,
        logger: ILogger,
        interval_seconds: float = 0.5,
        simulate_connection_errors: bool = False,
    ) -> None:
        """Initialize simulated exchange prices and streaming settings."""
        self._logger = logger.bind(module="MockExchangeAdapter")
        self._interval = interval_seconds
        self._simulate_errors = simulate_connection_errors
        self._connected = False
        self._subscribers: dict[str, list[TickCallback]] = {}
        self._stream_task: asyncio.Task[None] | None = None

        # Base prices for realistic simulation
        self._prices: dict[str, Decimal] = {
            "BTC/USDT": Decimal("95000.00"),
            "ETH/USDT": Decimal("3500.00"),
            "SOL/USDT": Decimal("200.00"),
            "XAU/USD": Decimal("2350.50"),
            "EUR/USD": Decimal("1.0850"),
            "USD/JPY": Decimal("155.20"),
        }
        self._volatility: dict[str, float] = {
            "BTC/USDT": 0.0005,
            "ETH/USDT": 0.0008,
            "SOL/USDT": 0.0012,
            "XAU/USD": 0.0002,
            "EUR/USD": 0.0001,
            "USD/JPY": 0.00015,
        }

    @property
    def exchange_id(self) -> str:
        """Return identifier."""
        return "mock"

    async def connect(self) -> None:
        """Simulate connecting to exchange API."""
        if self._simulate_errors and random.random() < 0.2:
            raise InfrastructureException("Simulated random connection refusal from Mock Exchange")
        self._connected = True
        self._logger.info("Connected to Mock Exchange")

    async def disconnect(self) -> None:
        """Disconnect and stop background streaming task."""
        self._connected = False
        if self._stream_task and not self._stream_task.done():
            self._stream_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._stream_task
        self._subscribers.clear()
        self._logger.info("Disconnected from Mock Exchange")

    async def get_ticker(self, symbol: str) -> Tick:
        """Generate synthetic ticker."""
        self._ensure_connected()
        std_sym = symbol.strip().upper()
        price = self._step_price(std_sym)
        spread = price * Decimal("0.0002")
        return Tick(
            symbol=std_sym,
            price=price,
            volume=Decimal(str(round(random.uniform(0.1, 10.0), 4))),
            bid=price - spread,
            ask=price + spread,
            timestamp=datetime.now(UTC),
            exchange=self.exchange_id,
        )

    async def get_klines(self, symbol: str, timeframe: str, limit: int = 100) -> list[Kline]:
        """Generate synthetic historical candlestick bars."""
        self._ensure_connected()
        std_sym = symbol.strip().upper()
        current_price = self._prices.get(std_sym, Decimal("100.0"))
        tf_minutes = self._parse_timeframe_minutes(timeframe)
        duration = timedelta(minutes=tf_minutes)

        klines: list[Kline] = []
        now = datetime.now(UTC)
        # Round close time to minute
        close_time = now.replace(second=0, microsecond=0)

        price = current_price
        for i in range(limit - 1, -1, -1):
            bar_close_time = close_time - (duration * i)
            bar_open_time = bar_close_time - duration

            change = Decimal(str(random.uniform(-0.005, 0.005))) * price
            o = price
            c = price + change
            high_val = max(o, c) + (Decimal(str(random.uniform(0.0001, 0.002))) * price)
            low_val = min(o, c) - (Decimal(str(random.uniform(0.0001, 0.002))) * price)
            vol = Decimal(str(round(random.uniform(10.0, 500.0), 2)))

            klines.append(
                Kline(
                    symbol=std_sym,
                    timeframe=timeframe,
                    open_time=bar_open_time,
                    close_time=bar_close_time,
                    open=round(o, 4),
                    high=round(high_val, 4),
                    low=round(low_val, 4),
                    close=round(c, 4),
                    volume=vol,
                    is_closed=True,
                )
            )
            price = c

        return klines

    async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderBook:
        """Generate synthetic order book."""
        self._ensure_connected()
        std_sym = symbol.strip().upper()
        price = self._prices.get(std_sym, Decimal("100.0"))
        step = price * Decimal("0.0001")

        bids: list[OrderBookEntry] = []
        asks: list[OrderBookEntry] = []

        for i in range(1, limit + 1):
            bid_price = round(price - (step * Decimal(str(i))), 4)
            ask_price = round(price + (step * Decimal(str(i))), 4)
            amount = Decimal(str(round(random.uniform(0.5, 5.0), 2)))
            bids.append(OrderBookEntry(price=bid_price, amount=amount))
            asks.append(OrderBookEntry(price=ask_price, amount=amount))

        return OrderBook(
            symbol=std_sym,
            timestamp=datetime.now(UTC),
            bids=bids,
            asks=asks,
            exchange=self.exchange_id,
        )

    async def subscribe_ticks(self, symbols: list[str], callback: TickCallback) -> None:
        """Subscribe callbacks to simulated tick streaming."""
        self._ensure_connected()
        for sym in symbols:
            std_sym = sym.strip().upper()
            if std_sym not in self._subscribers:
                self._subscribers[std_sym] = []
            if callback not in self._subscribers[std_sym]:
                self._subscribers[std_sym].append(callback)

        if self._stream_task is None or self._stream_task.done():
            self._stream_task = asyncio.create_task(self._streaming_loop())
            self._logger.info("Started mock streaming loop", symbols=symbols)

    async def unsubscribe_ticks(self, symbols: list[str]) -> None:
        """Unsubscribe symbols."""
        for sym in symbols:
            std_sym = sym.strip().upper()
            self._subscribers.pop(std_sym, None)

    def is_connected(self) -> bool:
        """Check connection state."""
        return self._connected

    def _ensure_connected(self) -> None:
        if not self._connected:
            raise InfrastructureException(
                "MockExchangeAdapter is not connected. Call connect() first."
            )

    def _step_price(self, symbol: str) -> Decimal:
        """Random walk price step."""
        current = self._prices.get(symbol, Decimal("100.00"))
        vol = self._volatility.get(symbol, 0.001)
        change_pct = random.gauss(0, vol)
        new_price = current * Decimal(str(1.0 + change_pct))
        # Ensure positive
        if new_price <= Decimal("0"):
            new_price = Decimal("0.01")
        self._prices[symbol] = round(new_price, 4)
        return self._prices[symbol]

    async def _streaming_loop(self) -> None:
        """Background asyncio loop pushing synthetic ticks to subscribers."""
        while self._connected:
            try:
                await asyncio.sleep(self._interval)
                if not self._subscribers:
                    continue

                for sym, callbacks in list(self._subscribers.items()):
                    if not callbacks:
                        continue
                    price = self._step_price(sym)
                    spread = price * Decimal("0.0002")
                    tick = Tick(
                        symbol=sym,
                        price=price,
                        volume=Decimal(str(round(random.uniform(0.1, 5.0), 4))),
                        bid=price - spread,
                        ask=price + spread,
                        timestamp=datetime.now(UTC),
                        exchange=self.exchange_id,
                    )
                    for cb in list(callbacks):
                        try:
                            await cb(tick)
                        except Exception as e:
                            self._logger.error(
                                "Error invoking subscriber callback", symbol=sym, error=str(e)
                            )
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.exception("Unexpected error in mock streaming loop", error=str(e))

    def _parse_timeframe_minutes(self, timeframe: str) -> int:
        tf = timeframe.strip().lower()
        if tf.endswith("m"):
            return int(tf[:-1])
        if tf.endswith("h"):
            return int(tf[:-1]) * 60
        if tf.endswith("d"):
            return int(tf[:-1]) * 1440
        return 1
