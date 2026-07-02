"""Unit tests for Discord infrastructure adapters."""

from unittest.mock import MagicMock, patch

import pytest

from yukinoaaa.infrastructure.discord.mock_adapter import MockDiscordAdapter
from yukinoaaa.infrastructure.discord.webhook_adapter import DiscordWebhookAdapter
from yukinoaaa.infrastructure.logging.logger import StructlogLogger


@pytest.mark.asyncio
async def test_mock_discord_adapter_lifecycle_and_messaging() -> None:
    """Test start, stop, and in-memory logging of MockDiscordAdapter."""
    logger = StructlogLogger()
    adapter = MockDiscordAdapter(logger=logger)

    # When stopped, messaging should fail/return False
    assert not await adapter.send_notification("Test", "Msg")
    assert not await adapter.send_embed("Test", "Desc")

    await adapter.start()
    await adapter.start()  # Idempotent

    assert await adapter.send_notification("Alert", "System online", level="success")
    assert await adapter.send_embed(
        title="Trade Alert",
        description="Bought 1 BTC",
        color=0x00FF00,
        fields=[{"name": "Price", "value": "$68000", "inline": True}],
        footer="Footer text",
    )

    assert len(adapter.sent_messages) == 1
    assert adapter.sent_messages[0]["title"] == "Alert"
    assert len(adapter.sent_embeds) == 1
    assert adapter.sent_embeds[0]["fields"][0]["name"] == "Price"

    await adapter.stop()
    await adapter.stop()  # Idempotent
    assert not await adapter.send_notification("Post-stop", "Fail")


@pytest.mark.asyncio
async def test_discord_webhook_adapter() -> None:
    """Test DiscordWebhookAdapter URL formatting and mocked HTTP POST execution."""
    logger = StructlogLogger()
    adapter = DiscordWebhookAdapter(
        webhook_url="https://discord.com/api/webhooks/test/token", logger=logger
    )

    assert not await adapter.send_notification("Fail", "Stopped")
    assert not await adapter.send_embed("Fail", "Stopped")

    await adapter.start()

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.status = 204
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        # Test notification
        res1 = await adapter.send_notification("System Alert", "All nodes healthy", level="success")
        assert res1 is True
        assert mock_urlopen.call_count == 1

        # Test embed
        res2 = await adapter.send_embed(
            title="Portfolio Report",
            description="Daily summary",
            color=0x3498DB,
            fields=[{"name": "Equity", "value": "$10000", "inline": True}],
            footer="End report",
        )
        assert res2 is True
        assert mock_urlopen.call_count == 2

    # Test HTTP error handling
    with patch("urllib.request.urlopen") as mock_urlopen_err:
        mock_resp_err = MagicMock()
        mock_resp_err.status = 500
        mock_resp_err.__enter__.return_value = mock_resp_err
        mock_urlopen_err.return_value = mock_resp_err

        res3 = await adapter.send_notification("Err Test", "Should fail")
        assert res3 is False

    await adapter.stop()
