"""Structured logging interface."""

from abc import ABC, abstractmethod
from typing import Any


class ILogger(ABC):
    """Abstract interface for structured logging."""

    @abstractmethod
    def debug(self, event: str, **kwargs: Any) -> None:
        """Log a debug message."""
        ...

    @abstractmethod
    def info(self, event: str, **kwargs: Any) -> None:
        """Log an informational message."""
        ...

    @abstractmethod
    def warning(self, event: str, **kwargs: Any) -> None:
        """Log a warning message."""
        ...

    @abstractmethod
    def error(self, event: str, **kwargs: Any) -> None:
        """Log an error message."""
        ...

    @abstractmethod
    def critical(self, event: str, **kwargs: Any) -> None:
        """Log a critical message."""
        ...

    @abstractmethod
    def exception(self, event: str, **kwargs: Any) -> None:
        """Log an exception with stack trace."""
        ...

    @abstractmethod
    def bind(self, **kwargs: Any) -> "ILogger":
        """Bind contextual key-value pairs to the logger instance."""
        ...
