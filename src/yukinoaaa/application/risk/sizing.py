"""Position Sizing Calculator using Fixed Fractional Risk formula."""

from decimal import Decimal

from yukinoaaa.domain.exceptions import ValidationException
from yukinoaaa.domain.risk.models import RiskPolicy
from yukinoaaa.domain.trading.models import OrderSide


class PositionCalculator:
    """Calculates optimal position size based on account equity, stop-loss distance, and risk limits."""

    @staticmethod
    def calculate_position_size(
        equity: Decimal,
        entry_price: Decimal,
        side: OrderSide,
        stop_loss: Decimal | None,
        policy: RiskPolicy,
    ) -> tuple[Decimal, Decimal]:
        """Compute order quantity and stop-loss using fixed fractional sizing.

        Returns:
            tuple[Decimal, Decimal]: (approved_quantity, final_stop_loss)
        """
        if equity <= Decimal("0") or entry_price <= Decimal("0"):
            raise ValidationException("Equity and entry price must be positive for sizing calculation")

        # Determine effective stop-loss if omitted
        final_stop_loss = stop_loss
        if final_stop_loss is None or final_stop_loss <= Decimal("0"):
            if side == OrderSide.BUY:
                final_stop_loss = entry_price * (Decimal("1") - policy.default_stop_loss_percent)
            else:
                final_stop_loss = entry_price * (Decimal("1") + policy.default_stop_loss_percent)

        distance = abs(entry_price - final_stop_loss)
        if distance == Decimal("0"):
            raise ValidationException("Stop-loss distance cannot be zero")

        # Fixed fractional formula: Risk Amount = Equity * Max Risk %
        risk_amount = equity * policy.max_risk_per_trade_percent
        raw_quantity = risk_amount / distance

        # Check absolute USD position ceiling
        max_quantity_by_usd = policy.max_position_size_usd / entry_price
        approved_quantity = min(raw_quantity, max_quantity_by_usd).quantize(Decimal("0.000001"))

        if approved_quantity <= Decimal("0"):
            raise ValidationException("Calculated position size is zero or negative")

        return approved_quantity, final_stop_loss.quantize(Decimal("0.000001"))
