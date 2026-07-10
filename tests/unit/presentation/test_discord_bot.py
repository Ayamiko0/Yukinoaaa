"""Unit tests for Discord bot presentation layer and command routing."""

import pytest

from yukinoaaa.application.backtest.orchestrator import BacktestOrchestrator
from yukinoaaa.application.trading.portfolio_service import PortfolioService
from yukinoaaa.infrastructure.cache.redis_cache import RedisCache
from yukinoaaa.infrastructure.discord.mock_adapter import MockDiscordAdapter
from yukinoaaa.infrastructure.events.event_bus import AsyncEventBus
from yukinoaaa.infrastructure.logging.logger import StructlogLogger
from yukinoaaa.presentation.discord.bot import DiscordBot
from yukinoaaa.presentation.discord.commands import DiscordCommandRouter


@pytest.mark.asyncio
async def test_discord_command_router_execution() -> None:
    """Test slash commands and chat commands routing without external dependencies."""
    logger = StructlogLogger()
    cache = RedisCache(redis_url="redis://localhost:6379/0", logger=logger)
    event_bus = AsyncEventBus(logger=logger)
    portfolio = PortfolioService(
        cache=cache, event_bus=event_bus, logger=logger, default_account_id="TEST_ACC"
    )
    orchestrator = BacktestOrchestrator(logger=logger)

    router = DiscordCommandRouter(
        logger=logger, portfolio_service=portfolio, orchestrator=orchestrator
    )

    # Test /help
    res_help = await router.execute_command("/help")
    assert "Commands" in res_help["title"]

    # Test /status
    res_status = await router.execute_command("/status")
    assert "System Health Status" in res_status["title"]
    assert res_status["color"] == 0x2ECC71

    # Test /portfolio
    await portfolio.start()
    res_port = await router.execute_command("/portfolio")
    assert "Account Portfolio Snapshot" in res_port["title"]

    # Test /price multi-asset with /price <asset_class> <symbol> syntax
    res_price = await router.execute_command("/price CRYPTO ETH/USDT")
    assert "ETH/USDT" in res_price["title"]
    assert "CRYPTO" in res_price["description"]

    res_price_comm = await router.execute_command("/price COMMODITY XAU/USD")
    assert "XAU/USD" in res_price_comm["title"]

    res_price_forex = await router.execute_command("/price FOREX EUR/USD")
    assert "EUR/USD" in res_price_forex["title"]

    # Test /news
    res_news = await router.execute_command("/news MACRO")
    assert "Bản Tin & Tổng Quan Thị Trường" in res_news["title"]

    # Test /backtest
    res_bt = await router.execute_command("/backtest BTC/USDT")
    assert "Quantitative Backtest" in res_bt["title"]

    # Test unknown and empty
    res_unk = await router.execute_command("/unknown_cmd")
    assert "Unknown command" in res_unk["description"]

    res_empty = await router.execute_command("")
    assert "Empty command" in res_empty["description"]

    await portfolio.stop()
    await cache.close()


@pytest.mark.asyncio
async def test_discord_bot_interface() -> None:
    """Test DiscordBot presentation interface start, stop, and message interaction handling."""
    logger = StructlogLogger()
    mock_discord = MockDiscordAdapter(logger=logger)
    bot = DiscordBot(notification_service=mock_discord, logger=logger)

    # While stopped
    res_offline = await bot.handle_message("/status")
    assert res_offline["title"] == "Error"

    await bot.start()
    await bot.start()  # Idempotent

    res_online = await bot.handle_message("/status", user_id="user_123")
    assert res_online["title"] == "⚡ System Health Status"
    assert len(mock_discord.sent_embeds) == 1

    await bot.stop()
    await bot.stop()  # Idempotent


@pytest.mark.asyncio
async def test_discord_bot_sync_commands() -> None:
    """Test sync_commands early return when credentials missing."""
    logger = StructlogLogger()
    mock_discord = MockDiscordAdapter(logger=logger)
    bot = DiscordBot(notification_service=mock_discord, logger=logger)
    res = await bot.sync_commands("", "")
    assert res is False
