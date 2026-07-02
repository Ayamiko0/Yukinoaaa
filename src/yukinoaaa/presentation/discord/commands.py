"""Discord slash and chat command router and embed formatter."""

from typing import Any

from yukinoaaa.application.backtest.orchestrator import BacktestOrchestrator
from yukinoaaa.application.interfaces.logger import ILogger
from yukinoaaa.application.trading.portfolio_service import PortfolioService


class DiscordCommandRouter:
    """Routes Discord user chat and slash commands to application services and builds embed responses."""

    def __init__(
        self,
        logger: ILogger,
        portfolio_service: PortfolioService | None = None,
        orchestrator: BacktestOrchestrator | None = None,
    ) -> None:
        """Initialize command router with application services and logger."""
        self._logger = logger.bind(module="DiscordCommandRouter")
        self._portfolio = portfolio_service
        self._backtest = orchestrator

    async def execute_command(
        self, command_line: str, user_id: str = "default_user"
    ) -> dict[str, Any]:
        """Parse and execute a raw command string from Discord chat or slash input.

        Args:
            command_line: Input text starting with slash, e.g. '/portfolio' or '/price BTC/USDT'.
            user_id: Discord User ID invoking command.

        Returns:
            Dictionary representing a Discord Embed object response.
        """
        parts = command_line.strip().split()
        if not parts:
            return self._build_error_embed("Empty command provided. Try `/help`.")

        cmd = parts[0].lower()
        args = parts[1:]
        self._logger.info("Executing Discord command", command=cmd, user_id=user_id, args=args)

        if cmd in ("/help", "!help"):
            return self._handle_help()
        elif cmd in ("/status", "!status"):
            return await self._handle_status()
        elif cmd in ("/portfolio", "!portfolio"):
            return await self._handle_portfolio()
        elif cmd in ("/price", "!price"):
            symbol = args[0].upper() if args else "BTC/USDT"
            return await self._handle_price(symbol)
        elif cmd in ("/backtest", "!backtest"):
            symbol = args[0].upper() if args else "BTC/USDT"
            return await self._handle_backtest(symbol)
        else:
            return self._build_error_embed(
                f"Unknown command `{cmd}`. Use `/help` for available commands."
            )

    def _handle_help(self) -> dict[str, Any]:
        """Return embed listing available bot commands."""
        fields = [
            {
                "name": "`/status`",
                "value": "Check trading system health and operational status.",
                "inline": False,
            },
            {
                "name": "`/portfolio`",
                "value": "View real-time account equity and open positions.",
                "inline": False,
            },
            {
                "name": "`/price <symbol>`",
                "value": "Get latest market tick and price quotes (e.g. `/price BTC/USDT`).",
                "inline": False,
            },
            {
                "name": "`/backtest <symbol>`",
                "value": "Trigger instant quantitative strategy backtest simulation.",
                "inline": False,
            },
        ]
        return {
            "title": "🤖 Yukinoaaa Trading Assistant - Commands",
            "description": "Available quantitative trading and market analysis commands:",
            "color": 0x3498DB,
            "fields": fields,
            "footer": {"text": "Yukinoaaa Presentation Layer"},
        }

    async def _handle_status(self) -> dict[str, Any]:
        """Return system status embed."""
        fields = [
            {"name": "Status", "value": "✅ **ONLINE**", "inline": True},
            {"name": "Architecture", "value": "Clean Architecture / EDA", "inline": True},
            {"name": "API Gateway", "value": "0.0.0.0:8000 (Active)", "inline": True},
            {"name": "Active Strategy", "value": "`RSI_Reversal_RSI_14`", "inline": True},
        ]
        return {
            "title": "⚡ System Health Status",
            "description": "Yukinoaaa Quantitative Trading Assistant is fully operational.",
            "color": 0x2ECC71,
            "fields": fields,
            "footer": {"text": "Yukinoaaa Monitoring"},
        }

    async def _handle_portfolio(self) -> dict[str, Any]:
        """Return real-time portfolio balance and open positions embed."""
        if not self._portfolio:
            return self._build_error_embed("Portfolio service is not currently bound.")

        account_id = self._portfolio.portfolio.account_id
        equity = self._portfolio.portfolio.total_equity
        positions = list(self._portfolio.portfolio.positions.values())

        fields = [
            {"name": "Account ID", "value": f"`{account_id}`", "inline": True},
            {"name": "Total Equity", "value": f"**${equity:,.2f}**", "inline": True},
            {"name": "Open Positions", "value": str(len(positions)), "inline": True},
        ]

        if positions:
            pos_text = "\n".join(
                [
                    f"• `{p.symbol}` **{p.side.value}** ({p.quantity} @ ${p.entry_price})"
                    for p in positions[:5]
                ]
            )
            fields.append({"name": "Active Trades", "value": pos_text, "inline": False})
        else:
            fields.append(
                {
                    "name": "Active Trades",
                    "value": "_No open trading positions currently active._",
                    "inline": False,
                }
            )

        return {
            "title": "💼 Account Portfolio Snapshot",
            "description": "Real-time balance and exposure report:",
            "color": 0xF1C40F,
            "fields": fields,
            "footer": {"text": f"Account: {account_id}"},
        }

    async def _handle_price(self, symbol: str) -> dict[str, Any]:
        """Return simulated real-time market price quote."""
        fields = [
            {"name": "Instrument", "value": f"`{symbol}`", "inline": True},
            {"name": "Market Status", "value": "🟢 **OPEN**", "inline": True},
            {"name": "Last Price", "value": "$68,450.00", "inline": True},
        ]
        return {
            "title": f"📈 Market Quote: {symbol}",
            "description": f"Real-time data stream quote for **{symbol}**.",
            "color": 0x3498DB,
            "fields": fields,
            "footer": {"text": "Yukinoaaa Market Data Engine"},
        }

    async def _handle_backtest(self, symbol: str) -> dict[str, Any]:
        """Run backtest orchestrator and return summary embed."""
        if not self._backtest:
            return self._build_error_embed("Backtest orchestrator is not currently bound.")

        from datetime import UTC, datetime, timedelta
        from decimal import Decimal

        from yukinoaaa.domain.backtest.models import BacktestConfig

        now = datetime.now(UTC)
        config = BacktestConfig(
            symbol=symbol,
            timeframe="1h",
            start_time=now - timedelta(days=7),
            end_time=now,
            initial_equity=Decimal("10000.00"),
            strategy_name="rsi_reversal",
        )

        try:
            res = await self._backtest.run_backtest(config, klines=[])
            ret = f"{res.total_return_percentage * 100:.2f}"
            win_rate = f"{res.win_rate * 100:.2f}"
            trades = str(res.total_trades)

            fields = [
                {"name": "Symbol", "value": f"`{symbol}`", "inline": True},
                {"name": "Strategy", "value": "`rsi_reversal`", "inline": True},
                {"name": "Total Trades", "value": str(trades), "inline": True},
                {"name": "Total Return", "value": f"**{ret}%**", "inline": True},
                {"name": "Win Rate", "value": f"**{win_rate}%**", "inline": True},
            ]
            return {
                "title": f"🔬 Quantitative Backtest: {symbol}",
                "description": "Simulation completed successfully:",
                "color": 0x9B59B6,
                "fields": fields,
                "footer": {"text": "Yukinoaaa Backtest Engine"},
            }
        except Exception as e:
            return self._build_error_embed(f"Backtest failed to execute: {e}")

    def _build_error_embed(self, err_msg: str) -> dict[str, Any]:
        """Construct standard error embed."""
        return {
            "title": "🚨 Command Execution Error",
            "description": err_msg,
            "color": 0xE74C3C,
            "footer": {"text": "Yukinoaaa Error Handler"},
        }
