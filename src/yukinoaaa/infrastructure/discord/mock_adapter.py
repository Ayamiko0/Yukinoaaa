"""Mock Discord adapter for testing, dry-run mode, and local development."""

from typing import Any

from yukinoaaa.application.interfaces.logger import ILogger
from yukinoaaa.application.interfaces.notification import INotificationService


class MockDiscordAdapter(INotificationService):
    """In-memory mock Discord adapter logging messages without external network calls."""

    def __init__(self, logger: ILogger) -> None:
        """Initialize mock Discord adapter with structured logger."""
        self._logger = logger.bind(module="MockDiscordAdapter")
        self._is_running = False
        self.sent_messages: list[dict[str, Any]] = []
        self.sent_embeds: list[dict[str, Any]] = []

    async def start(self) -> None:
        """Start mock discord service."""
        if self._is_running:
            return
        self._is_running = True
        self._logger.info("Mock Discord adapter started successfully")

    async def stop(self) -> None:
        """Stop mock discord service."""
        if not self._is_running:
            return
        self._is_running = False
        self._logger.info("Mock Discord adapter stopped")

    async def send_notification(self, title: str, message: str, level: str = "info") -> bool:
        """Log text notification message in memory."""
        if not self._is_running:
            self._logger.warning(
                "Attempted to send notification while service stopped", title=title
            )
            return False

        payload = {"title": title, "message": message, "level": level}
        self.sent_messages.append(payload)
        self._logger.info("Discord Notification [MOCK]", title=title, level=level, message=message)
        return True

    async def send_embed(
        self,
        title: str,
        description: str,
        color: int = 0x3498DB,
        fields: list[dict[str, Any]] | None = None,
        footer: str | None = None,
    ) -> bool:
        """Log rich Discord embed in memory."""
        if not self._is_running:
            self._logger.warning("Attempted to send embed while service stopped", title=title)
            return False

        embed = {
            "title": title,
            "description": description,
            "color": color,
            "fields": fields or [],
            "footer": footer,
        }
        self.sent_embeds.append(embed)
        self._logger.info("Discord Embed [MOCK]", title=title, fields_count=len(fields or []))
        return True
