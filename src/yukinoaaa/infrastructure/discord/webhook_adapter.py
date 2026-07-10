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
        self._webhook_url = webhook_url.strip().strip("'\"")
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
        """Send a rich Discord embed card to webhook compliant with Discord API restrictions."""
        if not self._is_running:
            self._logger.warning("Attempted to send embed while adapter stopped", title=title)
            return False

        sanitized_title = str(title).strip()[:256] or "Yukinoaaa System Event"
        sanitized_desc = str(description).strip()[:4096] or "System Event"

        embed_obj: dict[str, Any] = {
            "title": sanitized_title,
            "description": sanitized_desc,
            "color": int(color) & 0xFFFFFF,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        total_len = len(sanitized_title) + len(sanitized_desc)

        if fields:
            sanitized_fields = []
            for f in fields[:25]:
                fname = str(f.get("name", "Field")).strip()[:256] or "Field"
                fval = str(f.get("value", "-")).strip()[:1024] or "-"
                finline = bool(f.get("inline", True))
                if total_len + len(fname) + len(fval) > 5800:
                    break
                total_len += len(fname) + len(fval)
                sanitized_fields.append({"name": fname, "value": fval, "inline": finline})
            embed_obj["fields"] = sanitized_fields

        if footer:
            embed_obj["footer"] = {"text": str(footer).strip()[:2048]}

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
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    "Accept": "application/json",
                    "Accept-Language": "en-US,en;q=0.9",
                },
                method="POST",
            )
            await asyncio.to_thread(self._send_http_request, req)
            self._logger.debug("Successfully dispatched Discord webhook message")
            return True
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            msg = (
                "Discord Webhook URL returned 404 Not Found. Verify DISCORD_WEBHOOK_URL in .env is valid."
                if e.code == 404
                else "Failed to dispatch Discord webhook message"
            )
            self._logger.error(
                msg,
                status_code=e.code,
                error=str(e),
                response_body=err_body,
            )
            return False
        except Exception as e:
            self._logger.error("Failed to dispatch Discord webhook message", error=str(e))
            return False

    def _send_http_request(self, req: urllib.request.Request) -> None:
        """Blocking urllib request execution."""
        with urllib.request.urlopen(req, timeout=5.0, context=self._ssl_context) as resp:
            if resp.status not in (200, 204):
                raise RuntimeError(f"Unexpected HTTP status {resp.status} from Discord")
