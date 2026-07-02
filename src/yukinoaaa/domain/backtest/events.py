"""Backtest domain events for Event-Driven Architecture."""

from yukinoaaa.domain.events import DomainEvent


class BacktestStartedEvent(DomainEvent):
    """Event emitted when a backtest replay session begins."""


class BacktestCompletedEvent(DomainEvent):
    """Event emitted when a backtest replay session finishes and metrics are calculated."""


class BacktestProgressEvent(DomainEvent):
    """Event emitted periodically to report backtest execution progress."""
