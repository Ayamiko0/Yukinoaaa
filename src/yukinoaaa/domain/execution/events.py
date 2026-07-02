"""Execution domain events for Event-Driven Architecture."""

from yukinoaaa.domain.events import DomainEvent


class OrderSubmittedEvent(DomainEvent):
    """Event emitted when an order is successfully accepted by exchange or simulator."""


class OrderPartiallyFilledEvent(DomainEvent):
    """Event emitted when an order receives a partial fill."""


class OrderExecutionCompletedEvent(DomainEvent):
    """Event emitted when an order reaches a terminal state (FILLED, CANCELLED, REJECTED, FAILED)."""


class ExecutionReportReceivedEvent(DomainEvent):
    """Event emitted when a raw execution report arrives from an adapter."""
