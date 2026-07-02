"""Risk Engine orchestrator handling signals, capital protection, and emergency halts."""

from decimal import Decimal
from typing import Any
from yukinoaaa.application.interfaces.event_bus import IEventBus
from yukinoaaa.application.interfaces.logger import ILogger
from yukinoaaa.application.risk.validator import RiskValidator
from yukinoaaa.application.trading.portfolio_service import PortfolioService
from yukinoaaa.domain.events import DomainEvent
from yukinoaaa.domain.risk.events import RiskEvaluatedEvent, RiskLimitExceededEvent, TradingHaltedEvent
from yukinoaaa.domain.risk.models import RiskDecision, RiskPolicy, RiskReport, RiskStatus
from yukinoaaa.domain.trading.events import OrderCreatedEvent
from yukinoaaa.domain.trading.models import Order, OrderType


class RiskEngine:
    """Orchestrates risk evaluation of signals and enforces account protection limits."""

    def __init__(
        self,
        portfolio_service: PortfolioService,
        validator: RiskValidator,
        policy: RiskPolicy,
        event_bus: IEventBus,
        logger: ILogger,
    ) -> None:
        """Initialize risk engine with policy, validator, and event bus."""
        self._portfolio_service = portfolio_service
        self._validator = validator
        self._policy = policy
        self._event_bus = event_bus
        self._logger = logger.bind(module="RiskEngine")

        # Account risk tracking state
        self._peak_equity = self._portfolio_service.portfolio.total_equity
        self._daily_realized_pnl = Decimal("0.0")
        self._is_halted = False
        self._running = False

    @property
    def is_halted(self) -> bool:
        """Return True if account trading is frozen due to risk breach."""
        return self._is_halted

    def get_risk_report(self) -> RiskReport:
        """Generate real-time diagnostic risk report."""
        port = self._portfolio_service.portfolio
        equity = port.total_equity
        if equity > self._peak_equity:
            self._peak_equity = equity

        drawdown_pct = Decimal("0.0")
        if self._peak_equity > Decimal("0"):
            drawdown_pct = (self._peak_equity - equity) / self._peak_equity
            if drawdown_pct < Decimal("0"):
                drawdown_pct = Decimal("0.0")

        daily_loss_pct = Decimal("0.0")
        if self._daily_realized_pnl < Decimal("0") and self._peak_equity > Decimal("0"):
            daily_loss_pct = abs(self._daily_realized_pnl) / self._peak_equity

        return RiskReport(
            account_id=port.account_id,
            total_equity=equity,
            peak_equity=self._peak_equity,
            daily_realized_pnl=self._daily_realized_pnl,
            current_drawdown_percent=drawdown_pct,
            daily_loss_percent=daily_loss_pct,
            is_trading_halted=self._is_halted,
        )

    async def start(self) -> None:
        """Subscribe to trade signals and position close events."""
        if self._running:
            return
        self._running = True
        await self._event_bus.subscribe("SignalCreated", self._on_signal_created)
        await self._event_bus.subscribe("PositionClosed", self._on_position_closed)
        self._logger.info("Risk engine started")

    async def stop(self) -> None:
        """Unsubscribe from events."""
        if not self._running:
            return
        self._running = False
        await self._event_bus.unsubscribe("SignalCreated", self._on_signal_created)
        await self._event_bus.unsubscribe("PositionClosed", self._on_position_closed)
        self._logger.info("Risk engine stopped")

    async def _on_position_closed(self, event: DomainEvent) -> None:
        """Update daily PnL and check if drawdown/loss limits trigger emergency halt."""
        if not self._running:
            return

        payload: dict[str, Any] = event.payload
        pnl_str = payload.get("realized_pnl")
        if pnl_str:
            try:
                pnl = Decimal(str(pnl_str))
                self._daily_realized_pnl += pnl
                report = self.get_risk_report()

                # Check if limits breached
                if report.current_drawdown_percent >= self._policy.max_drawdown_percent or report.daily_loss_percent >= self._policy.max_daily_loss_percent:
                    self._is_halted = True
                    self._logger.error(
                        "EMERGENCY HALT TRIGGERED",
                        drawdown=str(report.current_drawdown_percent),
                        daily_loss=str(report.daily_loss_percent),
                    )
                    await self._event_bus.publish(
                        RiskLimitExceededEvent(
                            event_type="RiskLimitExceeded",
                            payload={"account_id": report.account_id, "reason": "Max drawdown or daily loss exceeded"},
                        )
                    )
                    await self._event_bus.publish(
                        TradingHaltedEvent(
                            event_type="TradingHalted",
                            payload={"account_id": report.account_id, "is_halted": True},
                        )
                    )
            except Exception as e:
                self._logger.error("Error updating risk state on position close", error=str(e))

    async def _on_signal_created(self, event: DomainEvent) -> None:
        """Evaluate incoming trade signal against risk policies."""
        if not self._running:
            return

        payload: dict[str, Any] = event.payload
        signal_id = str(payload.get("signal_id", ""))
        sym = str(payload.get("symbol", "")).strip().upper()
        side_str = str(payload.get("side", "")).strip().upper()
        target_str = payload.get("target_price")
        stop_str = payload.get("stop_loss")

        if not sym or not side_str:
            return

        # Estimate current market price from open position or default fallback
        port = self._portfolio_service.portfolio
        current_price = Decimal("100.0")
        if sym in port.positions:
            current_price = port.positions[sym].mark_price
        elif payload.get("price") or payload.get("entry_price"):
            current_price = Decimal(str(payload.get("price") or payload.get("entry_price")))
        elif target_str and stop_str:
            # Estimate entry price midway or default
            current_price = (Decimal(str(target_str)) + Decimal(str(stop_str))) / Decimal("2.0")

        from yukinoaaa.domain.trading.models import OrderSide, TradeSignal

        try:
            signal = TradeSignal(
                signal_id=signal_id or "sig_manual",
                symbol=sym,
                timeframe=str(payload.get("timeframe", "1m")),
                side=OrderSide(side_str),
                strategy_name=str(payload.get("strategy_name", "Unknown")),
                target_price=Decimal(str(target_str)) if target_str else None,
                stop_loss=Decimal(str(stop_str)) if stop_str else None,
            )

            report = self.get_risk_report()
            decision: RiskDecision = self._validator.validate(signal, current_price, port, report)

            self._logger.info(
                "Risk evaluation completed",
                signal_id=signal.signal_id,
                status=decision.status.value,
                reason=decision.reason,
                approved_qty=str(decision.approved_quantity) if decision.approved_quantity else None,
            )

            await self._event_bus.publish(
                RiskEvaluatedEvent(
                    event_type="RiskEvaluated",
                    payload={
                        "decision_id": decision.decision_id,
                        "signal_id": signal.signal_id,
                        "status": decision.status.value,
                        "reason": decision.reason,
                        "approved_quantity": str(decision.approved_quantity) if decision.approved_quantity else None,
                    },
                )
            )

            if decision.status in (RiskStatus.APPROVED, RiskStatus.MODIFIED) and decision.approved_quantity:
                order = Order(
                    symbol=signal.symbol,
                    side=signal.side,
                    order_type=OrderType.MARKET,
                    price=current_price,
                    quantity=decision.approved_quantity,
                )
                port.add_order(order)
                await self._event_bus.publish(
                    OrderCreatedEvent(
                        event_type="OrderCreated",
                        payload={
                            "order_id": order.id,
                            "symbol": order.symbol,
                            "side": order.side.value,
                            "order_type": order.order_type.value,
                            "quantity": str(order.quantity),
                            "price": str(order.price) if order.price else None,
                        },
                    )
                )
        except Exception as e:
            self._logger.error("Error evaluating risk for signal", signal_id=signal_id, error=str(e))
