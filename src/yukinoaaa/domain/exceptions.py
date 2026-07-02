"""Domain layer exceptions.

This module defines base exceptions for the core domain.
Infrastructure and application errors should inherit from or wrap these exceptions
when crossing domain boundaries.
"""

from typing import Any


class YukinoaaaException(Exception):
    """Base exception for all Yukinoaaa system errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class DomainException(YukinoaaaException):
    """Base exception for domain business rule violations."""


class ValidationException(DomainException):
    """Raised when data or domain state validation fails."""


class RiskViolationException(DomainException):
    """Raised when a trading signal or order violates risk management rules."""


class ResourceNotFoundException(DomainException):
    """Raised when a required domain entity or resource is not found."""


class InfrastructureException(YukinoaaaException):
    """Base exception for technical infrastructure failures (database, redis, exchange)."""
