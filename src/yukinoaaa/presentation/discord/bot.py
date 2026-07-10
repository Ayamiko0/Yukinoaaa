"""Discord Bot presentation interface managing command routing and notification dispatches."""

from typing import Any

from yukinoaaa.application.ai.service import MarketAnalysisAIService
from yukinoaaa.application.backtest.orchestrator import BacktestOrchestrator
from yukinoaaa.application.interfaces.logger import ILogger
from yukinoaaa.application.interfaces.notification import INotificationService
from yukinoaaa.application.trading.portfolio_service import PortfolioService
from yukinoaaa.presentation.discord.commands import DiscordCommandRouter


class DiscordBot:
    """Presentation layer Discord Bot interface handling slash commands and alerts without external SDKs."""

    def __init__(
        self,
        notification_service: INotificationService,
        logger: ILogger,
        portfolio_service: PortfolioService | None = None,
        orchestrator: BacktestOrchestrator | None = None,
        ai_service: MarketAnalysisAIService | None = None,
    ) -> None:
        """Initialize Discord bot with notification adapter and command router."""
        self._notifier = notification_service
        self._logger = logger.bind(module="DiscordBot")
        self._router = DiscordCommandRouter(
            logger=logger,
            portfolio_service=portfolio_service,
            orchestrator=orchestrator,
            ai_service=ai_service,
        )
        self._is_running = False

    async def start(self) -> None:
        """Start Discord bot interface."""
        if self._is_running:
            return
        await self._notifier.start()
        self._is_running = True
        self._logger.info("Discord Bot presentation interface initialized and listening")

    async def sync_commands(
        self, bot_token: str, application_id: str, guild_id: str | None = None
    ) -> bool:
        """Asynchronously sync all slash commands (including /ai) to Discord API v10."""
        import aiohttp

        token = bot_token.strip().strip("'\"")
        if token.lower().startswith("bot "):
            token = token[4:].strip()
        app_id = application_id.strip().strip("'\"")
        if not token or not app_id:
            self._logger.warning("Discord credentials missing, skipping slash command registration")
            return False

        common_meta = {"integration_types": [0, 1], "contexts": [0, 1, 2]}
        commands = [
            {
                "name": "help",
                "description": "Hiển thị danh sách lệnh hỗ trợ Yukinoaaa Trading Assistant",
                **common_meta,
            },
            {
                "name": "status",
                "description": "Kiểm tra tình trạng sức khỏe hệ thống Yukinoaaa",
                **common_meta,
            },
            {
                "name": "portfolio",
                "description": "Xem báo cáo tổng quan tài khoản giao dịch",
                **common_meta,
            },
            {
                "name": "price",
                "description": "Tra cứu giá thị trường đa tài sản (Crypto, Forex, Vàng/Bạc/Dầu)",
                "options": [
                    {
                        "name": "asset_class",
                        "description": "Phân loại tài sản (Crypto, Forex, Commodity)",
                        "type": 3,
                        "required": False,
                        "choices": [
                            {"name": "Crypto (Tiền điện tử: BTC, ETH, SOL...)", "value": "CRYPTO"},
                            {"name": "Forex (Ngoại hối: EUR/USD, GBP/USD...)", "value": "FOREX"},
                            {
                                "name": "Commodity (Vàng XAU, Bạc XAG, Dầu WTI...)",
                                "value": "COMMODITY",
                            },
                        ],
                    },
                    {
                        "name": "symbol",
                        "description": "Mã tài sản (Ví dụ: BTC/USDT, XAU/USD, EUR/USD, WTI/USD)",
                        "type": 3,
                        "required": False,
                    },
                ],
                **common_meta,
            },
            {
                "name": "news",
                "description": "Cập nhật, tóm tắt và tổng quan tin tức thị trường tài chính",
                "options": [
                    {
                        "name": "category",
                        "description": "Danh mục tin tức cần xem (Crypto, Vĩ mô, Hàng hóa, Forex)",
                        "type": 3,
                        "required": False,
                        "choices": [
                            {"name": "Toàn thị trường (All Markets)", "value": "ALL"},
                            {"name": "Vĩ mô toàn cầu (Global Macro)", "value": "MACRO"},
                            {"name": "Tiền điện tử (Crypto Markets)", "value": "CRYPTO"},
                            {"name": "Hàng hóa & Kim loại (Gold/Oil)", "value": "COMMODITY"},
                            {"name": "Ngoại hối (Forex)", "value": "FOREX"},
                        ],
                    }
                ],
                **common_meta,
            },
            {
                "name": "backtest",
                "description": "Chạy mô phỏng định lượng Backtest cho chiến lược",
                "options": [
                    {
                        "name": "symbol",
                        "description": "Cặp tiền giao dịch (Ví dụ: BTC/USDT)",
                        "type": 3,
                        "required": False,
                    }
                ],
                **common_meta,
            },
            {
                "name": "ai",
                "description": "Phân tích định lượng thị trường bằng Local LLM (Ollama)",
                "options": [
                    {
                        "name": "symbol",
                        "description": "Cặp tiền giao dịch (Ví dụ: BTC/USDT)",
                        "type": 3,
                        "required": False,
                    }
                ],
                **common_meta,
            },
            {
                "name": "analyze",
                "description": "Phân tích định lượng thị trường bằng Local LLM (Ollama)",
                "options": [
                    {
                        "name": "symbol",
                        "description": "Cặp tiền giao dịch (Ví dụ: BTC/USDT)",
                        "type": 3,
                        "required": False,
                    }
                ],
                **common_meta,
            },
        ]

        headers = {
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "DiscordBot (https://github.com/ayamiko0/Yukinoaaa, 0.1.0)",
        }

        urls = []
        if guild_id:
            urls.append(
                f"https://discord.com/api/v10/applications/{app_id}/guilds/{guild_id}/commands"
            )
        urls.append(f"https://discord.com/api/v10/applications/{app_id}/commands")

        success = False
        async with aiohttp.ClientSession(headers=headers) as session:
            for url in urls:
                try:
                    async with session.put(
                        url, json=commands, timeout=aiohttp.ClientTimeout(total=15)
                    ) as resp:
                        if resp.status in (200, 201):
                            self._logger.info("Successfully synced Discord slash commands", url=url)
                            success = True
                        else:
                            err = await resp.text()
                            self._logger.error(
                                "Failed syncing Discord commands",
                                status_code=resp.status,
                                error=err,
                            )
                except Exception as exc:
                    self._logger.error("Exception syncing Discord commands", error=str(exc))

        return success

    async def stop(self) -> None:
        """Stop Discord bot interface."""
        if not self._is_running:
            return
        await self._notifier.stop()
        self._is_running = False
        self._logger.info("Discord Bot interface shut down")

    async def handle_message(
        self, message_content: str, user_id: str = "default_user"
    ) -> dict[str, Any]:
        """Process incoming chat message or interaction and dispatch response embed.

        Args:
            message_content: Raw message text, e.g. '/portfolio'.
            user_id: Discord User ID.

        Returns:
            Embed response dictionary generated by command execution.
        """
        if not self._is_running:
            self._logger.warning("Message received while DiscordBot is stopped", user_id=user_id)
            return {"title": "Error", "description": "Bot is currently offline.", "color": 0xE74C3C}

        self._logger.debug(
            "Processing Discord message interaction", content=message_content, user_id=user_id
        )
        embed_response = await self._router.execute_command(message_content, user_id)

        # Dispatch response back via notification adapter
        await self._notifier.send_embed(
            title=str(embed_response.get("title", "Response")),
            description=str(embed_response.get("description", "")),
            color=int(embed_response.get("color", 0x3498DB)),
            fields=embed_response.get("fields"),
            footer=embed_response.get("footer", {}).get("text")
            if isinstance(embed_response.get("footer"), dict)
            else None,
        )
        return embed_response
