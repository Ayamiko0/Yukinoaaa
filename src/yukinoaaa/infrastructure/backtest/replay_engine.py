"""Historical Replay Engine pumping sequential klines and ticks into the Event Bus."""

import asyncio

from yukinoaaa.application.interfaces.event_bus import IEventBus
from yukinoaaa.application.interfaces.logger import ILogger
from yukinoaaa.domain.market.events import KlineReceivedEvent, TickReceivedEvent
from yukinoaaa.domain.market.models import Kline


class HistoricalReplayEngine:
    """Replays historical kline series sequentially to simulate real-time event flow."""

    def __init__(self, event_bus: IEventBus, logger: ILogger) -> None:
        """Initialize replay engine with event bus and structured logger."""
        self._event_bus = event_bus
        self._logger = logger.bind(module="HistoricalReplayEngine")

    async def replay_klines(self, klines: list[Kline], emit_ticks: bool = True) -> int:
        """Pump klines and close-price ticks sequentially into the event bus.

        Returns:
            int: Number of klines replayed.
        """
        if not klines:
            return 0

        # Ensure strict timestamp sorting
        sorted_klines = sorted(klines, key=lambda k: k.close_time)
        replayed_count = 0

        self._logger.info("Starting historical replay", total_klines=len(sorted_klines))

        for kline in sorted_klines:
            # Emit KlineReceivedEvent
            await self._event_bus.publish(
                KlineReceivedEvent(
                    event_type="KlineReceived",
                    payload={
                        "symbol": kline.symbol,
                        "timeframe": kline.timeframe,
                        "timestamp": kline.close_time.isoformat(),
                        "open": str(kline.open),
                        "high": str(kline.high),
                        "low": str(kline.low),
                        "close": str(kline.close),
                        "volume": str(kline.volume),
                        "is_closed": kline.is_closed,
                    },
                    timestamp=kline.close_time,
                )
            )

            # Emit simulated tick at close price to trigger limit/stop orders in FillSimulator
            if emit_ticks:
                await self._event_bus.publish(
                    TickReceivedEvent(
                        event_type="TickReceived",
                        payload={
                            "symbol": kline.symbol,
                            "price": str(kline.close),
                            "volume": str(kline.volume),
                        },
                        timestamp=kline.close_time,
                    )
                )

            # Yield execution to event loop to allow downstream synchronous event handlers to process
            await asyncio.sleep(0)
            replayed_count += 1

        self._logger.info("Completed historical replay", replayed=replayed_count)
        return replayed_count
