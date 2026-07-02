"""Contracts and abstract interfaces for notification and Discord messaging services."""

from abc import ABC, abstractmethod
from typing import Any


class INotificationService(ABC):
    """Abstract contract for sending real-time notifications and alerts to Discord or channels."""

    @abstractmethod
    async def start(self) -> None:
        """Start the notification service and any underlying connection pools."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the notification service and release network resources."""
        pass

    @abstractmethod
    async def send_notification(self, title: str, message: str, level: str = "info") -> bool:
        """Send a basic text notification message.

        Args:
            title: Title or header of the message.
            message: Main body content.
            level: Severity level ('info', 'success', 'warning', 'error').

        Returns:
            True if sent successfully, False otherwise.
        """
        pass

    @abstractmethod
    async def send_embed(
        self,
        title: str,
        description: str,
        color: int = 0x3498DB,
        fields: list[dict[str, Any]] | None = None,
        footer: str | None = None,
    ) -> bool:
        """Send a rich Discord embed message.

        Args:
            title: Embed header title.
            description: Embed main content description.
            color: Hex color code (e.g. 0x00FF00 for green, 0xFF0000 for red).
            fields: List of dictionaries with 'name', 'value', and optional 'inline' boolean.
            footer: Optional footer text.

        Returns:
            True if embed sent successfully, False otherwise.
        """
        pass
