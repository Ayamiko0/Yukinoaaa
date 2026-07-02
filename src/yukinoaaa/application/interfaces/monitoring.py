"""Monitoring and health check interfaces."""

from abc import ABC, abstractmethod
from typing import Any


class IHealthCheck(ABC):
    """Abstract interface for service health checking."""

    @abstractmethod
    async def check_health(self) -> dict[str, Any]:
        """Perform a health check on system components (database, redis, event bus).

        Returns a dictionary containing overall status ('healthy', 'degraded', 'unhealthy')
        and detailed component diagnostics.
        """
        ...
