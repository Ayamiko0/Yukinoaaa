"""Asynchronous Event Bus implementation."""

import asyncio
from collections import defaultdict

from yukinoaaa.application.interfaces.event_bus import EventHandler, IEventBus
from yukinoaaa.application.interfaces.logger import ILogger
from yukinoaaa.domain.events import DomainEvent


class AsyncEventBus(IEventBus):
    """In-memory asynchronous event bus using asyncio.Queue."""

    def __init__(self, logger: ILogger) -> None:
        """Initialize event bus with logger and queue."""
        self._logger = logger.bind(module="AsyncEventBus")
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._queue: asyncio.Queue[DomainEvent] = asyncio.Queue()
        self._running = False
        self._dispatch_task: asyncio.Task[None] | None = None

    async def publish(self, event: DomainEvent) -> None:
        """Publish an event to the background processing queue."""
        if not self._running:
            self._logger.warning("Event published while bus is stopped", event_type=event.event_type)
        await self._queue.put(event)
        self._logger.debug("Event queued for dispatch", event_id=str(event.event_id), event_type=event.event_type)

    async def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Register an async handler callback for an event type."""
        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)
            self._logger.debug("Handler subscribed", event_type=event_type, handler=handler.__name__)

    async def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Remove a previously registered handler callback."""
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)
            self._logger.debug("Handler unsubscribed", event_type=event_type, handler=handler.__name__)

    async def start(self) -> None:
        """Start the background event dispatch loop."""
        if self._running:
            return
        self._running = True
        self._dispatch_task = asyncio.create_task(self._dispatch_loop())
        self._logger.info("Event bus started")

    async def stop(self) -> None:
        """Stop processing events and cleanly shut down."""
        if not self._running:
            return
        self._running = False
        if self._dispatch_task and not self._dispatch_task.done():
            self._dispatch_task.cancel()
            try:
                await self._dispatch_task
            except asyncio.CancelledError:
                pass
        self._logger.info("Event bus stopped")

    async def _dispatch_loop(self) -> None:
        """Background loop pulling events from queue and notifying handlers."""
        while self._running:
            try:
                event = await self._queue.get()
                await self._notify_subscribers(event)
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.exception("Unexpected error in event dispatch loop", error=str(e))

    async def _notify_subscribers(self, event: DomainEvent) -> None:
        """Invoke all handlers subscribed to the event type."""
        handlers = list(self._subscribers.get(event.event_type, []))
        if not handlers:
            self._logger.debug("No subscribers for event", event_type=event.event_type)
            return

        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                self._logger.error(
                    "Error executing event handler",
                    event_type=event.event_type,
                    handler=handler.__name__,
                    error=str(e),
                )
