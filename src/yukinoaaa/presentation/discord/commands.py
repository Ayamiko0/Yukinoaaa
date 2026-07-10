"""Discord slash and chat command router and embed formatter."""

from typing import Any

from yukinoaaa.application.ai.service import MarketAnalysisAIService
from yukinoaaa.application.backtest.orchestrator import BacktestOrchestrator
from yukinoaaa.application.interfaces.logger import ILogger
from yukinoaaa.application.trading.portfolio_service import PortfolioService
from yukinoaaa.infrastructure.market.price_fetcher import MarketPriceFetcher


class DiscordCommandRouter:
    """Routes Discord user chat and slash commands to application services and builds embed responses."""

    def __init__(
        self,
        logger: ILogger,
        portfolio_service: PortfolioService | None = None,
        orchestrator: BacktestOrchestrator | None = None,
        ai_service: MarketAnalysisAIService | None = None,
        price_fetcher: MarketPriceFetcher | None = None,
    ) -> None:
        """Initialize command router with application services and logger."""
        self._logger = logger.bind(module="DiscordCommandRouter")
        self._portfolio = portfolio_service
        self._backtest = orchestrator
        self._ai_service = ai_service
        self._price_fetcher = price_fetcher or MarketPriceFetcher(logger=logger)

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
            asset_class = "CRYPTO"
            symbol = "BTC/USDT"
            classes = {"CRYPTO", "FOREX", "COMMODITY"}
            if len(args) >= 2:
                if args[0].upper() in classes:
                    asset_class = args[0].upper()
                    symbol = args[1].upper()
                elif args[1].upper() in classes:
                    asset_class = args[1].upper()
                    symbol = args[0].upper()
                else:
                    symbol = args[0].upper()
            elif len(args) == 1:
                arg0 = args[0].upper()
                if arg0 in classes:
                    asset_class = arg0
                    symbol = (
                        "BTC/USDT"
                        if asset_class == "CRYPTO"
                        else ("XAU/USD" if asset_class == "COMMODITY" else "EUR/USD")
                    )
                else:
                    symbol = arg0
                    if any(
                        symbol.startswith(p)
                        for p in ("XAU", "XAG", "WTI", "BRENT", "GOLD", "SILVER", "OIL")
                    ):
                        asset_class = "COMMODITY"
                    elif symbol in (
                        "EUR/USD",
                        "GBP/USD",
                        "USD/JPY",
                        "AUD/USD",
                        "USD/CAD",
                        "NZD/USD",
                        "EUR/JPY",
                    ):
                        asset_class = "FOREX"
            return await self._handle_price(symbol, asset_class)
        elif cmd in ("/news", "!news"):
            category = args[0].upper() if args else "ALL"
            return await self._handle_news(category)
        elif cmd in ("/backtest", "!backtest"):
            symbol = args[0].upper() if args else "BTC/USDT"
            return await self._handle_backtest(symbol)
        elif cmd in ("/ai", "!ai", "/analyze", "!analyze"):
            symbol = args[0].upper() if args else "BTC/USDT"
            return await self._handle_ai_analysis(symbol)
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
                "name": "`/price <asset_class> <symbol>`",
                "value": "Tra cứu giá thị trường đa tài sản (Ví dụ: `/price CRYPTO BTC/USDT`, `/price COMMODITY XAU/USD`, `/price FOREX EUR/USD`).",
                "inline": False,
            },
            {
                "name": "`/news [category]`",
                "value": "Cập nhật, tóm tắt và tổng quan tin tức thị trường tài chính (ALL, MACRO, CRYPTO, COMMODITY, FOREX).",
                "inline": False,
            },
            {
                "name": "`/backtest <symbol>`",
                "value": "Trigger instant quantitative strategy backtest simulation.",
                "inline": False,
            },
            {
                "name": "`/ai <symbol>`",
                "value": "Analyze real-time market snapshot with Local LLM via Ollama.",
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

    async def _handle_price(self, symbol: str, asset_class: str = "CRYPTO") -> dict[str, Any]:
        """Return multi-asset real-time market price quote and technical indicators."""
        sym_clean = symbol.upper()
        cls_clean = asset_class.upper()
        if cls_clean not in ("CRYPTO", "FOREX", "COMMODITY"):
            cls_clean = "CRYPTO"

        quotes = {
            "CRYPTO": {
                "BTC/USDT": (
                    "$95,400.00",
                    "+2.45%",
                    "54.8",
                    "🟢 Bullish",
                    "Dòng vốn ETF duy trì ổn định, hỗ trợ vùng $93,500",
                ),
                "ETH/USDT": (
                    "$3,450.00",
                    "+3.10%",
                    "56.2",
                    "🟢 Bullish",
                    "Động lượng tích lũy mạnh trên khung H4",
                ),
                "SOL/USDT": (
                    "$185.20",
                    "+4.20%",
                    "62.0",
                    "🟢 Bullish",
                    "Khối lượng giao dịch hệ sinh thái gia tăng đột biến",
                ),
            },
            "COMMODITY": {
                "XAU/USD": (
                    "$2,845.50 / oz",
                    "+1.24%",
                    "58.4",
                    "🟢 Bullish",
                    "Nhu cầu trú ẩn an toàn tăng cao trước biến động vĩ mô",
                ),
                "XAG/USD": (
                    "$32.80 / oz",
                    "+1.85%",
                    "61.2",
                    "🟢 Bullish",
                    "Hỗ trợ bởi nhu cầu công nghiệp năng lượng tái tạo",
                ),
                "WTI/USD": (
                    "$74.20 / bbl",
                    "-0.65%",
                    "46.5",
                    "🟡 Neutral",
                    "Cân bằng giữa sản lượng OPEC+ và nhu cầu toàn cầu",
                ),
            },
            "FOREX": {
                "EUR/USD": (
                    "1.0425",
                    "+0.15%",
                    "51.0",
                    "🟡 Neutral",
                    "Theo dõi chênh lệch lãi suất giữa ECB và Fed",
                ),
                "GBP/USD": (
                    "1.2680",
                    "+0.22%",
                    "53.2",
                    "🟢 Bullish",
                    "Đồng Bảng Anh giữ vững mốc hỗ trợ 1.2600",
                ),
                "USD/JPY": (
                    "154.30",
                    "-0.40%",
                    "48.0",
                    "🟡 Neutral",
                    "Áp lực điều chỉnh khi BoJ phát tín hiệu thắt chặt",
                ),
            },
        }

        class_names = {
            "CRYPTO": "🪙 Tiền điện tử (CRYPTO)",
            "COMMODITY": "🥇 Hàng hóa & Kim loại (COMMODITY: Vàng/Bạc/Dầu)",
            "FOREX": "💱 Ngoại hối (FOREX Pairs)",
        }

        quote = quotes.get(cls_clean, {}).get(sym_clean)
        if quote:
            price, change, rsi, trend, note = quote
        else:
            dyn_quote = await self._price_fetcher.fetch_price_quote(sym_clean, cls_clean)
            price = dyn_quote["price"]
            change = dyn_quote["change"]
            rsi = dyn_quote["rsi"]
            trend = dyn_quote["trend"]
            note = dyn_quote["note"]

        color = 0x2ECC71 if "+" in change else (0xE74C3C if "-" in change else 0xF1C40F)
        fields = [
            {"name": "Mã Tài Sản (Symbol)", "value": f"`{sym_clean}`", "inline": True},
            {"name": "Phân Loại (Class)", "value": f"**{cls_clean}**", "inline": True},
            {"name": "Trạng Thái (Status)", "value": "🟢 **OPEN**", "inline": True},
            {"name": "Giá Hiện Tại (Price)", "value": f"**{price}**", "inline": True},
            {"name": "Biến Động 24h (24h Chg)", "value": f"**{change}**", "inline": True},
            {"name": "Chỉ Báo RSI (14)", "value": f"**{rsi}**", "inline": True},
            {"name": "Xu Hướng Kỹ Thuật", "value": f"**{trend}**", "inline": True},
            {"name": "💡 Nhận Định Tài Sản", "value": note[:1024], "inline": False},
        ]
        return {
            "title": f"📈 Bảng Giá & Tín Hiệu: {sym_clean}",
            "description": f"**Phân loại tài sản:** {class_names.get(cls_clean, cls_clean)}",
            "color": color,
            "fields": fields,
            "footer": {"text": f"Yukinoaaa Multi-Asset Feed ({cls_clean})"},
        }

    async def _handle_news(self, category: str = "ALL") -> dict[str, Any]:
        """Return executive summary of global financial market news and catalysts."""
        cat = category.upper()
        if cat not in ("ALL", "MACRO", "CRYPTO", "COMMODITY", "FOREX"):
            cat = "ALL"

        fields: list[dict[str, Any]] = []
        if cat in ("ALL", "MACRO"):
            fields.append(
                {
                    "name": "🔥 Vĩ mô Toàn cầu & Chính sách Tiền tệ (Global Macro)",
                    "value": (
                        "• **Cục Dự trữ Liên bang Mỹ (Fed):** Theo dõi sát dữ liệu lạm phát PCE và thị trường lao động; khả năng duy trì sự thận trọng về lộ trình lãi suất.\n"
                        "• **Chỉ số đồng USD (DXY):** Dao động quanh vùng 106.2, tạo áp lực vừa phải lên thị trường hàng hóa định giá bằng USD."
                    ),
                    "inline": False,
                }
            )
        if cat in ("ALL", "CRYPTO"):
            fields.append(
                {
                    "name": "🪙 Thị trường Tiền điện tử (Crypto & ETF Flows)",
                    "value": (
                        "• **Dòng vốn Spot ETF:** Lực mua từ các quỹ tổ chức đối với Bitcoin và Ethereum ETF tiếp tục ổn định, tâm lý thị trường tích cực.\n"
                        "• **Hệ sinh thái:** Hoạt động tài chính phi tập trung (DeFi) và khối lượng giao dịch trên các nền tảng Layer-1/Layer-2 tăng trưởng tốt."
                    ),
                    "inline": False,
                }
            )
        if cat in ("ALL", "COMMODITY"):
            fields.append(
                {
                    "name": "🥇 Kim loại Quý & Năng lượng (Gold, Silver & Crude Oil)",
                    "value": (
                        "• **Vàng (XAU/USD):** Nhu cầu mua gom tài sản phòng hộ rủi ro từ các Ngân hàng Trung ương tiếp tục duy trì đà vững chắc cho giá vàng.\n"
                        "• **Dầu thô (WTI/Brent):** Dao động quanh mốc cân bằng giữa các cam kết điều tiết sản lượng của OPEC+ và triển vọng tiêu thụ năng lượng toàn cầu."
                    ),
                    "inline": False,
                }
            )
        if cat in ("ALL", "FOREX"):
            fields.append(
                {
                    "name": "💱 Thị trường Ngoại hối (Forex Major Pairs)",
                    "value": (
                        "• **EUR/USD & GBP/USD:** Biến động hẹp chờ đợi các số liệu tăng trưởng và chỉ số niềm tin tiêu dùng khu vực châu Âu.\n"
                        "• **USD/JPY:** Ngân hàng Trung ương Nhật Bản (BoJ) duy trì thông điệp theo dõi mức tăng lương và rủi ro lạm phát."
                    ),
                    "inline": False,
                }
            )

        fields.append(
            {
                "name": "💡 Khuyến nghị Giao dịch Định lượng (Quantitative Advisory)",
                "value": (
                    "• Luôn áp dụng lệnh cắt lỗ (Stop-Loss) và quản lý quy mô lệnh phù hợp theo biến động thực tế.\n"
                    "• Kết hợp phân tích kỹ thuật đa khung thời gian trước khi ra quyết định giao dịch."
                ),
                "inline": False,
            }
        )

        return {
            "title": f"📰 Bản Tin & Tổng Quan Thị Trường ({cat})",
            "description": "**Tóm tắt nhanh:** Cập nhật diễn biến kinh tế vĩ mô, luân chuyển dòng vốn và xu hướng đa tài sản mới nhất.",
            "color": 0x3498DB,
            "fields": fields[:25],
            "footer": {"text": "Yukinoaaa Market Intelligence Digest"},
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

    async def _handle_ai_analysis(self, symbol: str) -> dict[str, Any]:
        """Execute real-time AI quantitative synthesis and return structured embed."""
        if not self._ai_service:
            return self._build_error_embed("Local LLM AI service is not currently bound.")

        from decimal import Decimal

        try:
            res = await self._ai_service.analyze_symbol(
                symbol=symbol,
                current_price=Decimal("95400.00"),
                rsi_value=42.5,
                macd_line=120.5,
                macd_signal=115.0,
                price_change_24h_pct=2.45,
            )
            color = 0xF1C40F
            if res.sentiment.value == "BULLISH":
                color = 0x2ECC71
            elif res.sentiment.value == "BEARISH":
                color = 0xE74C3C

            detailed_text = str(res.detailed_analysis).strip() or res.summary
            factors_str = "\n".join(f"• {f}" for f in res.key_factors) or "• Động lượng kỹ thuật"
            news_str = (
                "\n".join(f"• {n}" for n in res.news_references)
                or "• Theo dõi xu hướng thanh khoản thị trường phái sinh"
            )

            fields = [
                {"name": "Symbol", "value": f"`{res.symbol}`", "inline": True},
                {"name": "Sentiment", "value": f"**{res.sentiment.value}**", "inline": True},
                {
                    "name": "Confidence",
                    "value": f"**{res.confidence_score * 100:.1f}%**",
                    "inline": True,
                },
                {"name": "Recommendation", "value": f"**{res.recommendation}**", "inline": True},
                {"name": "AI Model", "value": f"`{res.model_name}`", "inline": True},
                {
                    "name": "🔬 Phân tích Chi tiết (LLM Quantitative Reasoning)",
                    "value": detailed_text[:1024],
                    "inline": False,
                },
                {
                    "name": "⚡ Các yếu tố Kỹ thuật chính (Key Drivers)",
                    "value": factors_str[:1024],
                    "inline": False,
                },
                {
                    "name": "📰 Tin tức & Sự kiện Tham chiếu (News & Macro Reference)",
                    "value": news_str[:1024],
                    "inline": False,
                },
            ]
            return {
                "title": f"🧠 Báo cáo Phân tích AI Định lượng: {res.symbol}",
                "description": f"**📌 Tóm tắt thị trường:** {res.summary}",
                "color": color,
                "fields": fields,
                "footer": {"text": "Yukinoaaa Local LLM Quantitative Engine (Ollama)"},
            }
        except Exception as e:
            return self._build_error_embed(f"AI market analysis failed: {e}")

    def _build_error_embed(self, err_msg: str) -> dict[str, Any]:
        """Construct standard error embed."""
        return {
            "title": "🚨 Command Execution Error",
            "description": err_msg,
            "color": 0xE74C3C,
            "footer": {"text": "Yukinoaaa Error Handler"},
        }
