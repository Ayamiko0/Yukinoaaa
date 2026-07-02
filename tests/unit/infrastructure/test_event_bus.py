"""Tests for asynchronous event bus."""

import asyncio

import pytest

from yukinoaaa.domain.events import DomainEvent
from yukinoaaa.infrastructure.events.event_bus import AsyncEventBus
from yukinoaaa.infrastructure.logging.logger import StructlogLogger


@pytest.mark.asyncio
async def test_event_bus_pub_sub() -> None:
    """Verify event subscription, publishing, and handler invocation."""
    logger = StructlogLogger()
    bus = AsyncEventBus(logger=logger)

    received_events: list[DomainEvent] = []

    async def sample_handler(event: DomainEvent) -> None:
        received_events.append(event)

    await bus.subscribe("OrderPlaced", sample_handler)
    await bus.start()

    test_event = DomainEvent(event_type="OrderPlaced", payload={"order_id": "ORD-123"})
    await bus.publish(test_event)

    # Allow background task to process queue
    await asyncio.sleep(0.05)
    await bus.stop()

    assert len(received_events) == 1
    assert received_events[0].payload["order_id"] == "ORD-123"


@pytest.mark.asyncio
async def test_event_bus_unsubscribe() -> None:
    """Verify unsubscribing stops handler from receiving events."""
    logger = StructlogLogger()
    bus = AsyncEventBus(logger=logger)
    received = 0

    async def count_handler(event: DomainEvent) -> None:
        nonlocal received
        received += 1

    await bus.subscribe("Ping", count_handler)
    await bus.unsubscribe("Ping", count_handler)
    await bus.start()

    await bus.publish(DomainEvent(event_type="Ping"))
    await asyncio.sleep(0.05)
    await bus.stop()

    assert received == 0
