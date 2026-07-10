"""Contracts and abstract interfaces for infrastructure services."""

from yukinoaaa.application.interfaces.ai import IAIService
from yukinoaaa.application.interfaces.cache import ICache
from yukinoaaa.application.interfaces.config import IConfig
from yukinoaaa.application.interfaces.database import IDatabase, IRepository
from yukinoaaa.application.interfaces.event_bus import IEventBus
from yukinoaaa.application.interfaces.exchange import IExchangeAdapter
from yukinoaaa.application.interfaces.execution import IExecutionAdapter
from yukinoaaa.application.interfaces.indicator import IIndicator
from yukinoaaa.application.interfaces.logger import ILogger
from yukinoaaa.application.interfaces.monitoring import IHealthCheck
from yukinoaaa.application.interfaces.notification import INotificationService
from yukinoaaa.application.interfaces.strategy import IStrategy

__all__ = [
    "IAIService",
    "ICache",
    "IConfig",
    "IDatabase",
    "IEventBus",
    "IExchangeAdapter",
    "IExecutionAdapter",
    "IHealthCheck",
    "IIndicator",
    "ILogger",
    "INotificationService",
    "IRepository",
    "IStrategy",
]
