"""Tests for master ApplicationOrchestrator and lifecycle management."""

import asyncio
import socket
from datetime import UTC, datetime

import pytest

from yukinoaaa.domain.market.events import KlineReceivedEvent, TickReceivedEvent
from yukinoaaa.main import ApplicationOrchestrator


def get_free_port() -> int:
    """Find an available unused local TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.mark.asyncio
async def test_application_orchestrator_lifecycle_and_event_forwarding() -> None:
    """Verify orchestrator starts all layers, hooks SSE forwarding, and stops cleanly."""
    port = get_free_port()
    orchestrator = ApplicationOrchestrator(host="127.0.0.1", port=port, redis_url="redis://localhost:59999/0")

    assert not orchestrator._is_running

    await orchestrator.start()
    await asyncio.sleep(0.05)

    try:
        assert orchestrator._is_running
        assert orchestrator._api_server._is_running

        # Test forwarding TickReceivedEvent and KlineReceivedEvent
        now = datetime.now(UTC)
        tick = TickReceivedEvent(
            event_type="TickReceived",
            payload={"symbol": "BTC/USDT", "price": "95000.00", "volume": "1.5"},
            timestamp=now,
        )
        await orchestrator._on_market_event(tick)

        kline = KlineReceivedEvent(
            event_type="KlineReceived",
            payload={"symbol": "BTC/USDT", "timeframe": "1m", "open": "94900", "high": "95100", "low": "94800", "close": "95000", "volume": "10"},
            timestamp=now,
        )
        await orchestrator._on_market_event(kline)
    finally:
        await orchestrator.stop()
        await asyncio.sleep(0.05)
        assert not orchestrator._is_running
