"""Risk domain events for Event-Driven Architecture."""

from yukinoaaa.domain.events import DomainEvent


class RiskEvaluatedEvent(DomainEvent):
    """Event emitted when a trade signal is evaluated by the risk engine."""


class RiskLimitExceededEvent(DomainEvent):
    """Event emitted when daily loss or total drawdown thresholds are exceeded."""


class TradingHaltedEvent(DomainEvent):
    """Event emitted when account trading is frozen due to capital protection limits."""
