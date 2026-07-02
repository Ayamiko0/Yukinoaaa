"""Market Cache Service for persisting real-time state and publishing events."""

from typing import Any
from yukinoaaa.application.interfaces.cache import ICache
from yukinoaaa.application.interfaces.event_bus import IEventBus
from yukinoaaa.application.interfaces.logger import ILogger
from yukinoaaa.domain.market.events import KlineReceivedEvent, MarketSnapshotUpdatedEvent, TickReceivedEvent
from yukinoaaa.domain.market.models import Kline, MarketSnapshot, OrderBook, Tick


class MarketCacheService:
    """Coordinates caching of ticks, klines, orderbooks and emits real-time domain events."""

    def __init__(self, cache: ICache, event_bus: IEventBus, logger: ILogger) -> None:
        """Initialize service with infrastructure contracts."""
        self._cache = cache
        self._event_bus = event_bus
        self._logger = logger.bind(module="MarketCacheService")
        self._memory_snapshots: dict[str, MarketSnapshot] = {}

    async def process_tick(self, tick: Tick) -> MarketSnapshot:
        """Update cache with new tick and publish events."""
        symbol = tick.symbol
        current_snapshot = await self.get_snapshot(symbol)

        new_snapshot = MarketSnapshot(
            symbol=symbol,
            last_tick=tick,
            last_kline=current_snapshot.last_kline if current_snapshot else None,
            orderbook=current_snapshot.orderbook if current_snapshot else None,
            timestamp=tick.timestamp,
        )

        await self._save_snapshot(new_snapshot)

        # Publish domain events asynchronously
        await self._event_bus.publish(
            TickReceivedEvent(
                event_type="TickReceived",
                payload={"symbol": symbol, "price": str(tick.price), "volume": str(tick.volume)},
            )
        )
        await self._event_bus.publish(
            MarketSnapshotUpdatedEvent(
                event_type="MarketSnapshotUpdated",
                payload={"symbol": symbol, "timestamp": tick.timestamp.isoformat()},
            )
        )
        return new_snapshot

    async def process_kline(self, kline: Kline) -> MarketSnapshot:
        """Update cache with new kline bar and publish events."""
        symbol = kline.symbol
        current_snapshot = await self.get_snapshot(symbol)

        new_snapshot = MarketSnapshot(
            symbol=symbol,
            last_tick=current_snapshot.last_tick if current_snapshot else None,
            last_kline=kline,
            orderbook=current_snapshot.orderbook if current_snapshot else None,
            timestamp=kline.close_time,
        )

        await self._save_snapshot(new_snapshot)

        await self._event_bus.publish(
            KlineReceivedEvent(
                event_type="KlineReceived",
                payload={"symbol": symbol, "timeframe": kline.timeframe, "close": str(kline.close)},
            )
        )
        return new_snapshot

    async def process_orderbook(self, orderbook: OrderBook) -> MarketSnapshot:
        """Update cache with orderbook depth snapshot."""
        symbol = orderbook.symbol
        current_snapshot = await self.get_snapshot(symbol)

        new_snapshot = MarketSnapshot(
            symbol=symbol,
            last_tick=current_snapshot.last_tick if current_snapshot else None,
            last_kline=current_snapshot.last_kline if current_snapshot else None,
            orderbook=orderbook,
            timestamp=orderbook.timestamp,
        )

        await self._save_snapshot(new_snapshot)
        return new_snapshot

    async def get_snapshot(self, symbol: str) -> MarketSnapshot:
        """Retrieve current market snapshot from cache or memory fallback."""
        key = f"market:snapshot:{symbol.upper()}"
        try:
            val: dict[str, Any] | None = await self._cache.get(key)
            if val is not None and isinstance(val, dict):
                return MarketSnapshot.model_validate(val)
        except Exception as e:
            self._logger.warning("Failed to retrieve snapshot from cache", symbol=symbol, error=str(e))

        # Return from memory fallback or empty snapshot
        return self._memory_snapshots.get(symbol.upper(), MarketSnapshot(symbol=symbol.upper()))

    async def _save_snapshot(self, snapshot: MarketSnapshot) -> None:
        """Persist snapshot to Redis and memory."""
        symbol = snapshot.symbol.upper()
        self._memory_snapshots[symbol] = snapshot
        key = f"market:snapshot:{symbol}"
        try:
            # Dump model to dict/json for redis storage with 1-hour TTL
            data = snapshot.model_dump(mode="json")
            await self._cache.set(key, data, ttl_seconds=3600)
        except Exception as e:
            self._logger.warning("Failed to save snapshot to cache", symbol=symbol, error=str(e))
