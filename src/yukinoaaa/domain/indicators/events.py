"""Technical indicators domain events for Event-Driven Architecture."""

from yukinoaaa.domain.events import DomainEvent


class IndicatorUpdatedEvent(DomainEvent):
    """Event emitted when a technical indicator is newly calculated or updated."""
