"""Risk Validator performing multi-layer policy checks on trade signals."""

from decimal import Decimal

from yukinoaaa.application.risk.sizing import PositionCalculator
from yukinoaaa.domain.risk.models import RiskDecision, RiskPolicy, RiskReport, RiskStatus
from yukinoaaa.domain.trading.models import Portfolio, TradeSignal


class RiskValidator:
    """Evaluates trade setups against drawdown limits, reward ratios, and available balance."""

    def __init__(self, policy: RiskPolicy, sizing_calculator: PositionCalculator) -> None:
        """Initialize validator with risk policy and sizing service."""
        self._policy = policy
        self._sizing = sizing_calculator

    def validate(
        self,
        signal: TradeSignal,
        current_price: Decimal,
        portfolio: Portfolio,
        report: RiskReport,
    ) -> RiskDecision:
        """Execute multi-layer validation pipeline and return RiskDecision."""
        # Layer 1: System Halt & Drawdown check
        if report.is_trading_halted:
            return RiskDecision(
                status=RiskStatus.REJECTED,
                signal_id=signal.signal_id,
                reason="Account trading is halted due to max drawdown or daily loss limit",
            )

        if report.current_drawdown_percent >= self._policy.max_drawdown_percent:
            return RiskDecision(
                status=RiskStatus.REJECTED,
                signal_id=signal.signal_id,
                reason=f"Account drawdown {report.current_drawdown_percent * 100:.1f}% exceeds max allowed {self._policy.max_drawdown_percent * 100:.1f}%",
            )

        if report.daily_loss_percent >= self._policy.max_daily_loss_percent:
            return RiskDecision(
                status=RiskStatus.REJECTED,
                signal_id=signal.signal_id,
                reason=f"Daily loss {report.daily_loss_percent * 100:.1f}% exceeds limit {self._policy.max_daily_loss_percent * 100:.1f}%",
            )

        # Layer 2: Risk/Reward Ratio check
        if signal.target_price and signal.stop_loss:
            reward = abs(signal.target_price - current_price)
            risk = abs(current_price - signal.stop_loss)
            if risk > Decimal("0"):
                rr_ratio = reward / risk
                if rr_ratio < self._policy.min_risk_reward_ratio:
                    return RiskDecision(
                        status=RiskStatus.REJECTED,
                        signal_id=signal.signal_id,
                        reason=f"Risk/Reward ratio {rr_ratio:.2f} is below required minimum {self._policy.min_risk_reward_ratio}",
                    )

        # Layer 3: Position Sizing & Available Balance check
        try:
            calc_qty, final_stop = self._sizing.calculate_position_size(
                equity=portfolio.total_equity,
                entry_price=current_price,
                side=signal.side,
                stop_loss=signal.stop_loss,
                policy=self._policy,
            )
        except Exception as e:
            return RiskDecision(
                status=RiskStatus.REJECTED,
                signal_id=signal.signal_id,
                reason=f"Sizing calculation failed: {str(e)}",
            )

        required_margin = calc_qty * current_price
        if required_margin > portfolio.available_balance:
            # Modify quantity to fit available balance
            max_affordable_qty = (portfolio.available_balance / current_price).quantize(
                Decimal("0.000001")
            )
            if max_affordable_qty <= Decimal("0"):
                return RiskDecision(
                    status=RiskStatus.REJECTED,
                    signal_id=signal.signal_id,
                    reason="Insufficient available balance to open position",
                )
            return RiskDecision(
                status=RiskStatus.MODIFIED,
                signal_id=signal.signal_id,
                reason=f"Quantity reduced from {calc_qty} to {max_affordable_qty} due to available balance ceiling",
                approved_quantity=max_affordable_qty,
                approved_leverage=Decimal("1.0"),
                target_price=signal.target_price,
                stop_loss=final_stop,
            )

        return RiskDecision(
            status=RiskStatus.APPROVED,
            signal_id=signal.signal_id,
            approved_quantity=calc_qty,
            approved_leverage=Decimal("1.0"),
            target_price=signal.target_price,
            stop_loss=final_stop,
        )
