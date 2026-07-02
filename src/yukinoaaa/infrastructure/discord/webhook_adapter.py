"""Zero-dependency Discord webhook adapter using asyncio and Python standard urllib."""

import asyncio
import json
import ssl
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any

from yukinoaaa.application.interfaces.logger import ILogger
from yukinoaaa.application.interfaces.notification import INotificationService


class DiscordWebhookAdapter(INotificationService):
    """Asynchronous Discord Webhook client sending formatted embeds via REST API."""

    def __init__(self, webhook_url: str, logger: ILogger) -> None:
        """Initialize webhook client with destination URL and structured logger."""
        self._webhook_url = webhook_url
        self._logger = logger.bind(module="DiscordWebhookAdapter")
        self._is_running = False
        self._ssl_context = ssl.create_default_context()

    async def start(self) -> None:
        """Start discord webhook client."""
        if self._is_running:
            return
        self._is_running = True
        self._logger.info("Discord Webhook adapter initialized and active")

    async def stop(self) -> None:
        """Stop discord webhook client."""
        if not self._is_running:
            return
        self._is_running = False
        self._logger.info("Discord Webhook adapter stopped")

    async def send_notification(self, title: str, message: str, level: str = "info") -> bool:
        """Send a standard text message to Discord webhook."""
        if not self._is_running:
            self._logger.warning(
                "Attempted to send notification while adapter stopped", title=title
            )
            return False

        icons = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "🚨",
        }
        icon = icons.get(level.lower(), "💬")
        content = f"{icon} **[{level.upper()}] {title}**\n{message}"
        payload = {"content": content}
        return await self._post_payload(payload)

    async def send_embed(
        self,
        title: str,
        description: str,
        color: int = 0x3498DB,
        fields: list[dict[str, Any]] | None = None,
        footer: str | None = None,
    ) -> bool:
        """Send a rich Discord embed card to webhook."""
        if not self._is_running:
            self._logger.warning("Attempted to send embed while adapter stopped", title=title)
            return False

        embed_obj: dict[str, Any] = {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        if fields:
            embed_obj["fields"] = fields
        if footer:
            embed_obj["footer"] = {"text": footer}

        payload = {"embeds": [embed_obj]}
        return await self._post_payload(payload)

    async def _post_payload(self, payload: dict[str, Any]) -> bool:
        """Execute synchronous HTTP POST inside asyncio worker thread."""
        try:
            data_bytes = json.dumps(payload, default=str).encode("utf-8")
            req = urllib.request.Request(
                self._webhook_url,
                data=data_bytes,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "User-Agent": "Yukinoaaa-Discord-Bot/1.0",
                },
                method="POST",
            )
            await asyncio.to_thread(self._send_http_request, req)
            self._logger.debug("Successfully dispatched Discord webhook message")
            return True
        except Exception as e:
            self._logger.error("Failed to dispatch Discord webhook message", error=str(e))
            return False

    def _send_http_request(self, req: urllib.request.Request) -> None:
        """Blocking urllib request execution."""
        with urllib.request.urlopen(req, timeout=5.0, context=self._ssl_context) as resp:
            if resp.status not in (200, 204):
                raise RuntimeError(f"Unexpected HTTP status {resp.status} from Discord")
