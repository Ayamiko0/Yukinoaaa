"""Health check service implementation."""

from datetime import datetime, timezone
from typing import Any
from yukinoaaa.application.interfaces.cache import ICache
from yukinoaaa.application.interfaces.database import IDatabase
from yukinoaaa.application.interfaces.logger import ILogger
from yukinoaaa.application.interfaces.monitoring import IHealthCheck


class HealthCheckService(IHealthCheck):
    """Service to diagnose system component health."""

    def __init__(
        self,
        database: IDatabase | None = None,
        cache: ICache | None = None,
        logger: ILogger | None = None,
    ) -> None:
        """Initialize health check service with system infrastructure components."""
        self._database = database
        self._cache = cache
        self._logger = logger.bind(module="HealthCheck") if logger else None

    async def check_health(self) -> dict[str, Any]:
        """Run health checks on database and cache components."""
        components: dict[str, Any] = {}
        overall_status = "healthy"

        # Check Database
        if self._database:
            try:
                # Basic check: verify connect does not raise
                await self._database.connect()
                components["database"] = {"status": "up"}
            except Exception as e:
                components["database"] = {"status": "down", "error": str(e)}
                overall_status = "unhealthy"
                if self._logger:
                    self._logger.error("Database health check failed", error=str(e))
        else:
            components["database"] = {"status": "not_configured"}

        # Check Redis/Cache
        if self._cache:
            try:
                await self._cache.set("health_ping", "pong", ttl_seconds=5)
                val = await self._cache.get("health_ping")
                if val == "pong":
                    components["cache"] = {"status": "up"}
                else:
                    components["cache"] = {"status": "degraded", "detail": "Ping mismatch"}
                    if overall_status == "healthy":
                        overall_status = "degraded"
            except Exception as e:
                components["cache"] = {"status": "down", "error": str(e)}
                if overall_status == "healthy":
                    overall_status = "degraded"
                if self._logger:
                    self._logger.warning("Cache health check failed", error=str(e))
        else:
            components["cache"] = {"status": "not_configured"}

        report = {
            "status": overall_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": components,
        }
        if self._logger:
            self._logger.info("Health check completed", overall_status=overall_status)
        return report
