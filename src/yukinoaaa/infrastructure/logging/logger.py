"""Structured logger implementation using Structlog."""

import logging
import sys
from typing import Any

import structlog

from yukinoaaa.application.interfaces.logger import ILogger


class StructlogLogger(ILogger):
    """Structured logging service implementation."""

    def __init__(self, log_level: str = "INFO", is_production: bool = False) -> None:
        """Initialize structlog configuration."""
        self._level = getattr(logging, log_level.upper(), logging.INFO)
        self._is_production = is_production
        self._configure_structlog()
        self._logger = structlog.get_logger()

    def _configure_structlog(self) -> None:
        """Configure processors and rendering based on application environment."""
        logging.basicConfig(format="%(message)s", stream=sys.stdout, level=self._level)

        processors: list[Any] = [
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
        ]

        if self._is_production:
            processors.append(structlog.processors.JSONRenderer())
        else:
            processors.append(structlog.dev.ConsoleRenderer(colors=True))

        structlog.configure(
            processors=processors,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

    def debug(self, event: str, **kwargs: Any) -> None:
        """Log a debug message."""
        self._logger.debug(event, **kwargs)

    def info(self, event: str, **kwargs: Any) -> None:
        """Log an informational message."""
        self._logger.info(event, **kwargs)

    def warning(self, event: str, **kwargs: Any) -> None:
        """Log a warning message."""
        self._logger.warning(event, **kwargs)

    def error(self, event: str, **kwargs: Any) -> None:
        """Log an error message."""
        self._logger.error(event, **kwargs)

    def critical(self, event: str, **kwargs: Any) -> None:
        """Log a critical message."""
        self._logger.critical(event, **kwargs)

    def exception(self, event: str, **kwargs: Any) -> None:
        """Log an exception with stack trace."""
        self._logger.exception(event, **kwargs)

    def bind(self, **kwargs: Any) -> "ILogger":
        """Bind contextual key-value pairs to a new logger instance."""
        bound = StructlogLogger.__new__(StructlogLogger)
        bound._logger = self._logger.bind(**kwargs)
        bound._level = self._level
        bound._is_production = self._is_production
        return bound
