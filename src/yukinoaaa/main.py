"""Production runtime bootstrapper and application lifecycle orchestrator."""

import asyncio
import signal
from typing import TYPE_CHECKING

from yukinoaaa.application.ai.service import MarketAnalysisAIService
from yukinoaaa.application.backtest.orchestrator import BacktestOrchestrator
from yukinoaaa.application.execution.manager import OrderManager
from yukinoaaa.application.execution.router import OrderRouter
from yukinoaaa.application.indicators.engine import IndicatorEngine
from yukinoaaa.application.market.cache_service import MarketCacheService
from yukinoaaa.application.market.normalizer import MarketNormalizer
from yukinoaaa.application.market.streamer import MarketDataStreamer
from yukinoaaa.application.market.validator import MarketValidator
from yukinoaaa.application.risk.engine import RiskEngine
from yukinoaaa.application.risk.sizing import PositionCalculator
from yukinoaaa.application.risk.validator import RiskValidator
from yukinoaaa.application.trading.notification_service import TradingNotificationService
from yukinoaaa.application.trading.portfolio_service import PortfolioService
from yukinoaaa.application.trading.strategies.rsi_reversal import RsiReversalStrategy
from yukinoaaa.application.trading.strategy_engine import StrategyEngine
from yukinoaaa.domain.events import DomainEvent
from yukinoaaa.domain.market.events import KlineReceivedEvent, TickReceivedEvent
from yukinoaaa.domain.risk.models import RiskPolicy
from yukinoaaa.infrastructure.ai.mock_adapter import MockAIAdapter
from yukinoaaa.infrastructure.ai.ollama_adapter import OllamaAIAdapter
from yukinoaaa.infrastructure.cache.redis_cache import RedisCache
from yukinoaaa.infrastructure.config.loader import Settings
from yukinoaaa.infrastructure.discord.mock_adapter import MockDiscordAdapter
from yukinoaaa.infrastructure.discord.webhook_adapter import DiscordWebhookAdapter
from yukinoaaa.infrastructure.events.event_bus import AsyncEventBus
from yukinoaaa.infrastructure.exchange.mock_adapter import MockExchangeAdapter
from yukinoaaa.infrastructure.execution.fill_simulator import FillSimulator
from yukinoaaa.infrastructure.logging.logger import StructlogLogger
from yukinoaaa.presentation.api.server import AsyncApiServer
from yukinoaaa.presentation.discord.bot import DiscordBot

if TYPE_CHECKING:
    from yukinoaaa.application.interfaces.ai import IAIService
    from yukinoaaa.application.interfaces.notification import INotificationService


class ApplicationOrchestrator:
    """Master orchestrator managing lifecycle of all 7 Clean Architecture layers."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8000,
        redis_url: str = "redis://localhost:6379/0",
    ) -> None:
        """Initialize all system components without starting IO loops."""
        self._logger = StructlogLogger().bind(module="ApplicationOrchestrator")
        self._redis_url = redis_url
        self._host = host
        self._port = port

        # Infrastructure Layer
        self._cache = RedisCache(redis_url=redis_url, logger=self._logger)
        self._event_bus = AsyncEventBus(logger=self._logger)
        self._exchange = MockExchangeAdapter(logger=self._logger)

        # Portfolio & Account
        self._portfolio_service = PortfolioService(
            cache=self._cache,
            event_bus=self._event_bus,
            logger=self._logger,
            default_account_id="PROD_ACCOUNT_01",
        )

        # Market Data Layer
        self._validator = MarketValidator(logger=self._logger)
        self._normalizer = MarketNormalizer(logger=self._logger)
        self._cache_service = MarketCacheService(
            cache=self._cache, event_bus=self._event_bus, logger=self._logger
        )
        self._streamer = MarketDataStreamer(
            adapter=self._exchange,
            cache_service=self._cache_service,
            validator=self._validator,
            normalizer=self._normalizer,
            event_bus=self._event_bus,
            logger=self._logger,
        )

        # Indicators & Strategies
        self._indicator_engine = IndicatorEngine(event_bus=self._event_bus, logger=self._logger)
        self._strategy_engine = StrategyEngine(event_bus=self._event_bus, logger=self._logger)

        # Risk Layer
        self._policy = RiskPolicy()
        self._sizing_calc = PositionCalculator()
        self._risk_validator = RiskValidator(
            policy=self._policy, sizing_calculator=self._sizing_calc
        )
        self._risk_engine = RiskEngine(
            portfolio_service=self._portfolio_service,
            validator=self._risk_validator,
            policy=self._policy,
            event_bus=self._event_bus,
            logger=self._logger,
        )

        # Execution Layer
        self._router = OrderRouter(
            portfolio_service=self._portfolio_service,
            event_bus=self._event_bus,
            logger=self._logger,
        )
        self._simulator = FillSimulator(
            event_bus=self._event_bus,
            logger=self._logger,
        )
        self._order_manager = OrderManager(
            portfolio_service=self._portfolio_service,
            event_bus=self._event_bus,
            logger=self._logger,
        )
        self._backtest_orchestrator = BacktestOrchestrator(
            logger=self._logger,
            redis_url=redis_url,
        )

        # AI & Local LLM Layer
        settings = Settings()
        self._ai_adapter: IAIService
        if settings.ollama_enabled:
            self._ai_adapter = OllamaAIAdapter(
                base_url=settings.ollama_base_url,
                model=settings.ollama_model,
                num_ctx=settings.ollama_num_ctx,
                num_predict=settings.ollama_num_predict,
                temperature=settings.ollama_temperature,
                timeout_sec=settings.ollama_timeout_sec,
                logger=self._logger,
            )
        else:
            self._ai_adapter = MockAIAdapter(logger=self._logger)
        self._ai_service = MarketAnalysisAIService(ai_service=self._ai_adapter, logger=self._logger)

        # Discord Integration Layer
        self._discord_adapter: INotificationService
        if settings.discord_webhook_url:
            self._discord_adapter = DiscordWebhookAdapter(
                webhook_url=settings.discord_webhook_url, logger=self._logger
            )
        else:
            self._discord_adapter = MockDiscordAdapter(logger=self._logger)
        self._notification_service = TradingNotificationService(
            notification_service=self._discord_adapter,
            event_bus=self._event_bus,
            logger=self._logger,
        )
        self._discord_bot = DiscordBot(
            notification_service=self._discord_adapter,
            logger=self._logger,
            portfolio_service=self._portfolio_service,
            orchestrator=self._backtest_orchestrator,
            ai_service=self._ai_service,
        )

        # Presentation Layer
        self._api_server = AsyncApiServer(
            host=host,
            port=port,
            logger=self._logger,
            portfolio_service=self._portfolio_service,
            orchestrator=self._backtest_orchestrator,
            discord_bot=self._discord_bot,
            discord_public_key=settings.discord_public_key,
            ai_service=self._ai_service,
        )

        self._is_running = False

    async def start(self) -> None:
        """Boot up cache, event bus, strategies, streamer, and API Gateway."""
        self._logger.info("Starting Yukinoaaa Trading Assistant platform...")
        await self._cache.exists("health_check_ping")

        # Register RSI Strategy
        rsi_strat = RsiReversalStrategy()
        self._strategy_engine.register_strategy(rsi_strat)

        # Hook API server to broadcast real-time market events via SSE
        await self._event_bus.subscribe("TickReceived", self._on_market_event)
        await self._event_bus.subscribe("KlineReceived", self._on_market_event)
        await self._event_bus.subscribe("OrderFilled", self._on_market_event)

        # Start core loops
        await self._event_bus.start()
        await self._portfolio_service.start()
        await self._order_manager.start()
        await self._streamer.start(["BTC/USDT"])
        await self._notification_service.start()
        await self._discord_bot.start()
        settings = Settings()
        if settings.discord_bot_token and settings.discord_application_id:
            await self._discord_bot.sync_commands(
                bot_token=settings.discord_bot_token,
                application_id=settings.discord_application_id,
                guild_id=settings.discord_guild_id,
            )
        await self._api_server.start()

        self._is_running = True
        self._logger.info(
            "Platform fully operational and listening", host=self._host, port=self._port
        )

    async def _on_market_event(self, event: DomainEvent) -> None:
        """Forward internal domain events to connected Web Dashboard SSE stream."""
        payload = event.payload
        if isinstance(event, TickReceivedEvent):
            await self._api_server.broadcast_event(
                "TickReceived",
                {
                    "symbol": str(payload.get("symbol", "")),
                    "price": str(payload.get("price", "")),
                    "timestamp": event.timestamp.isoformat(),
                },
            )
        elif isinstance(event, KlineReceivedEvent):
            await self._api_server.broadcast_event(
                "KlineReceived",
                {
                    "symbol": str(payload.get("symbol", "")),
                    "timeframe": str(payload.get("timeframe", "")),
                    "close": str(payload.get("close", "")),
                    "volume": str(payload.get("volume", "")),
                },
            )
        else:
            await self._api_server.broadcast_event(
                event.__class__.__name__,
                {"event_id": str(event.event_id), "timestamp": event.timestamp.isoformat()},
            )

    async def stop(self) -> None:
        """Gracefully shut down servers and close network IO connections."""
        if not self._is_running:
            return
        self._logger.info("Initiating graceful shutdown...")
        self._is_running = False

        await self._api_server.stop()
        await self._discord_bot.stop()
        await self._notification_service.stop()
        await self._streamer.stop()
        await self._order_manager.stop()
        await self._portfolio_service.stop()
        await self._event_bus.stop()
        await self._cache.close()
        self._logger.info("Shutdown complete. All resources cleanly released.")

    async def run_until_stopped(self) -> None:
        """Run blocking event loop until interrupted by OS termination signals."""
        await self._start_signal_handlers()
        await self.start()
        while self._is_running:
            await asyncio.sleep(0.5)

    async def _start_signal_handlers(self) -> None:
        """Register UNIX SIGINT and SIGTERM handlers for graceful shutdown."""
        loop = asyncio.get_running_loop()
        import contextlib

        for sig in (signal.SIGINT, signal.SIGTERM):
            with contextlib.suppress(NotImplementedError):
                loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))


async def main() -> None:
    """Main CLI execution entrypoint."""
    settings = Settings()
    orchestrator = ApplicationOrchestrator(
        host=settings.yukinoaaa_host,
        port=settings.yukinoaaa_port,
        redis_url=settings.redis_url,
    )
    try:
        await orchestrator.run_until_stopped()
    except asyncio.CancelledError:
        await orchestrator.stop()


if __name__ == "__main__":
    asyncio.run(main())
