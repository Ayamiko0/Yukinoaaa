"""Trading domain events for Event-Driven Architecture."""

from yukinoaaa.domain.events import DomainEvent


class OrderCreatedEvent(DomainEvent):
    """Event emitted when a trading order is created."""


class OrderFilledEvent(DomainEvent):
    """Event emitted when an order is filled by exchange or simulator."""


class OrderCancelledEvent(DomainEvent):
    """Event emitted when an order is cancelled."""


class PositionOpenedEvent(DomainEvent):
    """Event emitted when a new trading position is opened."""


class PositionClosedEvent(DomainEvent):
    """Event emitted when an active position is closed."""


class SignalCreatedEvent(DomainEvent):
    """Event emitted when a trading strategy generates a new quantitative trade signal."""
