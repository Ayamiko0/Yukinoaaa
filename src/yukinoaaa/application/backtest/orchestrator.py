"""Backtest Orchestrator tying all 5 phases into an isolated in-memory simulation environment."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from yukinoaaa.application.analytics.calculator import PerformanceCalculator
from yukinoaaa.application.execution.manager import OrderManager
from yukinoaaa.application.execution.router import OrderRouter
from yukinoaaa.application.indicators.engine import IndicatorEngine
from yukinoaaa.application.interfaces.logger import ILogger
from yukinoaaa.application.risk.engine import RiskEngine
from yukinoaaa.application.risk.sizing import PositionCalculator
from yukinoaaa.application.risk.validator import RiskValidator
from yukinoaaa.application.trading.portfolio_service import PortfolioService
from yukinoaaa.application.trading.strategy_engine import StrategyEngine
from yukinoaaa.domain.backtest.events import BacktestCompletedEvent, BacktestStartedEvent
from yukinoaaa.domain.backtest.models import BacktestConfig, PerformanceMetrics, TradeRecord
from yukinoaaa.domain.events import DomainEvent
from yukinoaaa.domain.risk.models import RiskPolicy
from yukinoaaa.infrastructure.backtest.replay_engine import HistoricalReplayEngine
from yukinoaaa.infrastructure.cache.redis_cache import RedisCache
from yukinoaaa.infrastructure.events.event_bus import AsyncEventBus
from yukinoaaa.infrastructure.execution.fill_simulator import FillSimulator
from yukinoaaa.infrastructure.execution.mock_adapter import MockExecutionAdapter


class BacktestOrchestrator:
    """Orchestrates historical data replay, event pipeline execution, and analytics report generation."""

    def __init__(self, logger: ILogger, redis_url: str = "redis://localhost:59999/0") -> None:
        """Initialize orchestrator with structured logger and cache connection URL."""
        self._logger = logger.bind(module="BacktestOrchestrator")
        self._redis_url = redis_url
        self._trades: list[TradeRecord] = []
        self._equity_curve: list[Decimal] = []
        self._portfolio_service: PortfolioService | None = None

    @property
    def trades(self) -> list[TradeRecord]:
        """Return list of recorded trade logs."""
        return self._trades

    @property
    def equity_curve(self) -> list[Decimal]:
        """Return recorded equity curve snapshots."""
        return self._equity_curve

    async def run_backtest(self, config: BacktestConfig, klines: list[Any]) -> PerformanceMetrics:
        """Execute end-to-end backtest simulation over provided kline series."""
        self._trades.clear()
        self._equity_curve.clear()
        self._equity_curve.append(config.initial_equity)

        bus = AsyncEventBus(logger=self._logger)
        cache = RedisCache(self._redis_url, self._logger)
        await bus.start()

        try:
            # 1. Trading Core (Phase 3B)
            port_service = PortfolioService(cache, bus, self._logger, default_account_id="acc_backtest")
            self._portfolio_service = port_service
            # Fund initial equity
            port_service.portfolio.available_balance = config.initial_equity

            # 2. Indicators Engine (Phase 3A)
            ind_engine = IndicatorEngine(bus, self._logger)

            # 3. Strategy Engine (Phase 3B)
            strat_engine = StrategyEngine(bus, self._logger)

            # 4. Risk Management Engine (Phase 4)
            policy = RiskPolicy(
                max_risk_per_trade_percent=Decimal("0.02"),
                max_position_size_usd=config.initial_equity * Decimal("5.0"),
            )
            validator = RiskValidator(policy, PositionCalculator())
            risk_engine = RiskEngine(port_service, validator, policy, bus, self._logger)

            # 5. Execution & Order Management Engine (Phase 5)
            simulator = FillSimulator(bus, self._logger, slippage_rate=config.slippage_rate, fee_rate=config.fee_rate)
            adapter = MockExecutionAdapter(
                port_service,
                fill_simulator=simulator,
                slippage_rate=config.slippage_rate,
                fee_rate=config.fee_rate,
            )
            router = OrderRouter(port_service, bus, self._logger)
            router.register_adapter("MOCK", adapter, is_default=True)
            manager = OrderManager(port_service, bus, self._logger)

            # 6. Historical Replay Engine (Phase 6)
            replay_engine = HistoricalReplayEngine(bus, self._logger)

            # Subscribe to tracking events
            await bus.subscribe("PositionClosed", self._on_position_closed)
            await bus.subscribe("KlineReceived", self._on_kline_received)

            # Start components
            await ind_engine.start()
            await strat_engine.start()
            await risk_engine.start()
            await simulator.start()
            await router.start()
            await manager.start()

            await bus.publish(
                BacktestStartedEvent(
                    event_type="BacktestStarted",
                    payload={"backtest_id": config.backtest_id, "symbol": config.symbol, "initial_equity": str(config.initial_equity)},
                )
            )

            # Replay data
            await replay_engine.replay_klines(klines, emit_ticks=True)

            # Compute metrics
            final_equity = port_service.portfolio.total_equity
            self._equity_curve.append(final_equity)

            metrics = PerformanceCalculator.calculate_metrics(
                initial_equity=config.initial_equity,
                final_equity=final_equity,
                trades=self._trades,
                equity_curve=self._equity_curve,
            )

            await bus.publish(
                BacktestCompletedEvent(
                    event_type="BacktestCompleted",
                    payload={
                        "backtest_id": config.backtest_id,
                        "total_return_percentage": str(metrics.total_return_percentage),
                        "total_trades": metrics.total_trades,
                        "sharpe_ratio": str(metrics.sharpe_ratio),
                    },
                )
            )

            # Stop components
            await manager.stop()
            await router.stop()
            await simulator.stop()
            await risk_engine.stop()
            await strat_engine.stop()
            await ind_engine.stop()

            return metrics
        finally:
            await bus.stop()
            await cache.close()

    async def _on_kline_received(self, event: DomainEvent) -> None:
        """Snapshot current equity on each kline step."""
        if self._portfolio_service:
            self._equity_curve.append(self._portfolio_service.portfolio.total_equity)

    async def _on_position_closed(self, event: DomainEvent) -> None:
        """Record completed trade log."""
        payload: dict[str, Any] = event.payload
        try:
            trade = TradeRecord(
                symbol=str(payload.get("symbol", "UNKNOWN")),
                side="LONG",
                entry_time=event.timestamp or datetime.now(timezone.utc),
                entry_price=Decimal("100.0"),
                exit_time=event.timestamp or datetime.now(timezone.utc),
                exit_price=Decimal("100.0"),
                quantity=Decimal("1.0"),
                realized_pnl=Decimal(str(payload.get("realized_pnl", "0.0"))),
                return_percentage=Decimal("0.05"),
                holding_duration_seconds=300,
            )
            self._trades.append(trade)
        except Exception as e:
            self._logger.error("Error logging trade record in orchestrator", error=str(e))

    @staticmethod
    def generate_markdown_report(config: BacktestConfig, metrics: PerformanceMetrics) -> str:
        """Format a GitHub-styled markdown summary table of backtest results."""
        return f"""# Quantitative Backtest Report

**Symbol:** `{config.symbol}` | **Timeframe:** `{config.timeframe}` | **Strategy:** `{config.strategy_name}`  
**Period:** `{config.start_time.strftime('%Y-%m-%d %H:%M')}` to `{config.end_time.strftime('%Y-%m-%d %H:%M')}`

## Performance Analytics Summary

| Metric | Value |
| :--- | :--- |
| **Initial Equity** | `${metrics.initial_equity:,.2f}` |
| **Final Equity** | `${metrics.final_equity:,.2f}` |
| **Total Return (%)** | `{metrics.total_return_percentage * 100:.2f}%` |
| **Total Trades** | `{metrics.total_trades}` (`{metrics.winning_trades}` Win / `{metrics.losing_trades}` Loss) |
| **Win Rate** | `{metrics.win_rate * 100:.2f}%` |
| **Total Realized PnL** | `${metrics.total_realized_pnl:,.2f}` |
| **Max Drawdown ($)** | `${metrics.max_drawdown_amount:,.2f}` (`{metrics.max_drawdown_percentage * 100:.2f}%`) |
| **Profit Factor** | `{metrics.profit_factor:.2f}` |
| **Sharpe Ratio** | `{metrics.sharpe_ratio:.2f}` |
| **Sortino Ratio** | `{metrics.sortino_ratio:.2f}` |
| **Average Trade PnL** | `${metrics.average_trade_pnl:,.2f}` |
| **Largest Win / Loss** | `${metrics.largest_win:,.2f}` / `${metrics.largest_loss:,.2f}` |
"""
