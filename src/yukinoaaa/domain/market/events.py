"""Market data domain events for Event-Driven Architecture."""

from yukinoaaa.domain.events import DomainEvent


class TickReceivedEvent(DomainEvent):
    """Event emitted when a validated and normalized market tick is processed."""


class KlineReceivedEvent(DomainEvent):
    """Event emitted when a new candlestick bar is updated or completed."""


class MarketSnapshotUpdatedEvent(DomainEvent):
    """Event emitted when a symbol's market cache snapshot is refreshed."""


class StreamDisconnectedEvent(DomainEvent):
    """Event emitted when an exchange real-time market data stream disconnects."""


class StreamReconnectedEvent(DomainEvent):
    """Event emitted when an exchange real-time market data stream successfully reconnects."""
