"""Market Data Streamer orchestrator with automatic exponential backoff reconnection."""

import asyncio

from yukinoaaa.application.interfaces.event_bus import IEventBus
from yukinoaaa.application.interfaces.exchange import IExchangeAdapter
from yukinoaaa.application.interfaces.logger import ILogger
from yukinoaaa.application.market.cache_service import MarketCacheService
from yukinoaaa.application.market.normalizer import MarketNormalizer
from yukinoaaa.application.market.validator import MarketValidator
from yukinoaaa.domain.market.events import StreamDisconnectedEvent, StreamReconnectedEvent
from yukinoaaa.domain.market.models import Tick


class MarketDataStreamer:
    """Orchestrates market streaming, validation, normalization, caching, and auto-reconnecting."""

    def __init__(
        self,
        adapter: IExchangeAdapter,
        cache_service: MarketCacheService,
        validator: MarketValidator,
        normalizer: MarketNormalizer,
        event_bus: IEventBus,
        logger: ILogger,
        max_reconnect_attempts: int = 10,
        initial_backoff_seconds: float = 1.0,
        max_backoff_seconds: float = 60.0,
    ) -> None:
        """Initialize market streamer orchestrator with dependencies and reconnect settings."""
        self._adapter = adapter
        self._cache_service = cache_service
        self._validator = validator
        self._normalizer = normalizer
        self._event_bus = event_bus
        self._logger = logger.bind(module="MarketDataStreamer", exchange=adapter.exchange_id)
        self._max_attempts = max_reconnect_attempts
        self._initial_backoff = initial_backoff_seconds
        self._max_backoff = max_backoff_seconds
        self._subscribed_symbols: list[str] = []
        self._running = False
        self._reconnect_task: asyncio.Task[None] | None = None

    async def start(self, symbols: list[str]) -> None:
        """Start streaming ticks for specified symbols with resilience."""
        if self._running:
            return
        self._running = True
        self._subscribed_symbols = [s.strip().upper() for s in symbols]
        self._logger.info("Starting market data streamer", symbols=self._subscribed_symbols)

        await self._connect_and_subscribe()

    async def stop(self) -> None:
        """Stop streaming and cleanly disconnect."""
        if not self._running:
            return
        self._running = False
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass
        try:
            await self._adapter.unsubscribe_ticks(self._subscribed_symbols)
            await self._adapter.disconnect()
        except Exception as e:
            self._logger.warning("Error during streamer shutdown", error=str(e))
        self._logger.info("Market data streamer stopped")

    async def _on_tick_callback(self, tick: Tick) -> None:
        """Callback invoked by exchange adapter when a raw tick arrives."""
        if not self._running:
            return

        # Step 1: Validate integrity
        if not self._validator.validate_tick(tick):
            return

        # Step 2: Normalize and check deduplication
        normalized = self._normalizer.normalize_and_deduplicate(tick)
        if normalized is None:
            return

        # Step 3: Save to cache and publish events
        try:
            await self._cache_service.process_tick(normalized)
        except Exception as e:
            self._logger.error("Error processing tick in cache service", symbol=tick.symbol, error=str(e))
            self._trigger_reconnect("Cache service processing error")

    async def _connect_and_subscribe(self) -> None:
        """Attempt connection and subscription."""
        try:
            await self._adapter.connect()
            await self._adapter.subscribe_ticks(self._subscribed_symbols, self._on_tick_callback)
            self._logger.info("Successfully connected and subscribed to stream")
        except Exception as e:
            self._logger.error("Initial connection failed, starting auto-reconnect", error=str(e))
            self._trigger_reconnect(str(e))

    def _trigger_reconnect(self, reason: str) -> None:
        """Trigger asynchronous auto-reconnection loop."""
        if not self._running:
            return
        if self._reconnect_task is None or self._reconnect_task.done():
            self._logger.warning("Stream disconnected, scheduling reconnect", reason=reason)
            self._reconnect_task = asyncio.create_task(self._auto_reconnect_loop(reason))

    async def _auto_reconnect_loop(self, reason: str) -> None:
        """Exponential backoff loop to restore exchange connection."""
        await self._event_bus.publish(
            StreamDisconnectedEvent(
                event_type="StreamDisconnected",
                payload={"exchange": self._adapter.exchange_id, "reason": reason},
            )
        )

        backoff = self._initial_backoff
        attempt = 1

        while self._running and attempt <= self._max_attempts:
            self._logger.info(
                "Attempting reconnection",
                attempt=attempt,
                max_attempts=self._max_attempts,
                backoff_seconds=backoff,
            )
            await asyncio.sleep(backoff)

            try:
                # Reset normalizer state on reconnect
                self._normalizer.reset_state(exchange=self._adapter.exchange_id)
                await self._adapter.disconnect()
                await self._adapter.connect()
                await self._adapter.subscribe_ticks(self._subscribed_symbols, self._on_tick_callback)

                self._logger.info("Stream successfully reconnected", attempt=attempt)
                await self._event_bus.publish(
                    StreamReconnectedEvent(
                        event_type="StreamReconnected",
                        payload={"exchange": self._adapter.exchange_id, "attempt": attempt},
                    )
                )
                return
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.warning("Reconnection attempt failed", attempt=attempt, error=str(e))
                attempt += 1
                backoff = min(backoff * 2, self._max_backoff)

        if self._running:
            self._logger.critical("Max reconnection attempts exhausted. Streamer halted.")
            self._running = False
