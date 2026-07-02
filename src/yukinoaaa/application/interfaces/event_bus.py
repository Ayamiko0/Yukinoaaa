"""Event bus interface for Event-Driven Architecture."""

from abc import ABC, abstractmethod
from collections.abc import Callable, Coroutine
from typing import Any

from yukinoaaa.domain.events import DomainEvent

# Type alias for async event handler callbacks
EventHandler = Callable[[DomainEvent], Coroutine[Any, Any, None]]


class IEventBus(ABC):
    """Abstract interface for publishing and subscribing to domain events."""

    @abstractmethod
    async def publish(self, event: DomainEvent) -> None:
        """Publish a domain event asynchronously to all subscribers."""
        ...

    @abstractmethod
    async def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe an async handler callback to a specific event type."""
        ...

    @abstractmethod
    async def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Unsubscribe a handler from a specific event type."""
        ...

    @abstractmethod
    async def start(self) -> None:
        """Start listening for and dispatching events in the background."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop processing events and cleanly shut down the event bus."""
        ...
