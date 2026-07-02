"""Tests for zero-dependency AsyncApiServer."""

import asyncio
import json
import socket
from urllib.request import Request, urlopen

import pytest

from yukinoaaa.infrastructure.logging.logger import StructlogLogger
from yukinoaaa.presentation.api.server import AsyncApiServer


def get_free_port() -> int:
    """Find an available unused local TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def fetch_url(url: str | Request) -> tuple[int, str]:
    """Helper to perform synchronous HTTP request."""
    with urlopen(url, timeout=3) as resp:
        return resp.status, resp.read().decode("utf-8")


@pytest.mark.asyncio
async def test_async_api_server_endpoints_and_static_serving() -> None:
    """Verify API server handles /health, /api/v1/portfolio, /api/v1/backtest, and static html serving."""
    logger = StructlogLogger()
    port = get_free_port()
    server = AsyncApiServer("127.0.0.1", port, logger)

    await server.start()
    await asyncio.sleep(0.05)

    try:
        # Test GET /health and /api/v1/health
        for health_path in ("/health", "/api/v1/health"):
            url_health = f"http://127.0.0.1:{port}{health_path}"
            status, content = await asyncio.to_thread(fetch_url, url_health)
            data = json.loads(content)
            assert status == 200
            assert data["status"] == "success"
            assert data["data"]["status"] == "ONLINE"

        # Test GET /api/v1/portfolio
        url_port = f"http://127.0.0.1:{port}/api/v1/portfolio"
        status, content = await asyncio.to_thread(fetch_url, url_port)
        data = json.loads(content)
        assert status == 200
        assert data["data"]["account_id"] == "acc_default"

        # Test POST /api/v1/backtest
        url_bt = f"http://127.0.0.1:{port}/api/v1/backtest"
        req_body = json.dumps({"symbol": "BTC/USDT", "initial_equity": "10000"}).encode("utf-8")
        req = Request(url_bt, data=req_body, headers={"Content-Type": "application/json"}, method="POST")
        status, content = await asyncio.to_thread(fetch_url, req)
        data = json.loads(content)
        assert status == 200
        assert "metrics" in data["data"]
        assert "report_markdown" in data["data"]

        # Test GET / (static index.html)
        url_index = f"http://127.0.0.1:{port}/"
        status, html = await asyncio.to_thread(fetch_url, url_index)
        assert status == 200
        assert "Yukinoaaa" in html
        assert "Real-Time Quant Studio" in html
    finally:
        await server.stop()
        await asyncio.sleep(0.05)


@pytest.mark.asyncio
async def test_async_api_server_discord_interactions() -> None:
    """Verify Discord HTTP Interactions Gateway handles ping and slash commands."""
    from yukinoaaa.infrastructure.discord.mock_adapter import MockDiscordAdapter
    from yukinoaaa.presentation.discord.bot import DiscordBot

    logger = StructlogLogger()
    mock_discord = MockDiscordAdapter(logger=logger)
    bot = DiscordBot(notification_service=mock_discord, logger=logger)
    port = get_free_port()
    server = AsyncApiServer("127.0.0.1", port, logger, discord_bot=bot)

    await bot.start()
    await server.start()
    await asyncio.sleep(0.05)

    try:
        url_interact = f"http://127.0.0.1:{port}/api/v1/discord/interactions"

        # 1. Test PING (Type 1)
        req_ping_body = json.dumps({"type": 1}).encode("utf-8")
        req_ping = Request(url_interact, data=req_ping_body, headers={"Content-Type": "application/json"}, method="POST")
        status, content = await asyncio.to_thread(fetch_url, req_ping)
        data = json.loads(content)
        assert status == 200
        assert data["type"] == 1

        # 2. Test APPLICATION_COMMAND /status (Type 2)
        req_cmd_body = json.dumps({
            "type": 2,
            "data": {"name": "status"},
            "member": {"user": {"id": "tester_101"}}
        }).encode("utf-8")
        req_cmd = Request(url_interact, data=req_cmd_body, headers={"Content-Type": "application/json"}, method="POST")
        status, content = await asyncio.to_thread(fetch_url, req_cmd)
        data = json.loads(content)
        assert status == 200
        assert data["type"] == 4
        assert "System Health Status" in data["data"]["embeds"][0]["title"]

        # 3. Test APPLICATION_COMMAND /price ETH/USDT with options
        req_price_body = json.dumps({
            "type": 2,
            "data": {
                "name": "price",
                "options": [{"name": "symbol", "value": "ETH/USDT"}]
            },
            "user": {"id": "tester_102"}
        }).encode("utf-8")
        req_price = Request(url_interact, data=req_price_body, headers={"Content-Type": "application/json"}, method="POST")
        status, content = await asyncio.to_thread(fetch_url, req_price)
        data = json.loads(content)
        assert status == 200
        assert data["type"] == 4
        assert "ETH/USDT" in data["data"]["embeds"][0]["title"]
    finally:
        await server.stop()
        await bot.stop()
        await asyncio.sleep(0.05)
