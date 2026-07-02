"""Risk domain models: RiskPolicy, RiskDecision, RiskReport, and RiskStatus."""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any
import uuid
from pydantic import BaseModel, ConfigDict, Field
from yukinoaaa.domain.exceptions import ValidationException


class RiskStatus(str, Enum):
    """Result status of a risk policy validation."""
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    MODIFIED = "MODIFIED"


class RiskPolicy(BaseModel):
    """Immutable configuration rules defining capital protection and sizing limits."""
    max_risk_per_trade_percent: Decimal = Field(
        default=Decimal("0.02"), ge=0, le=1.0, description="Max percentage of account equity at risk per trade (default 2%)"
    )
    max_daily_loss_percent: Decimal = Field(
        default=Decimal("0.05"), ge=0, le=1.0, description="Max daily drawdown percentage triggering emergency halt (default 5%)"
    )
    max_drawdown_percent: Decimal = Field(
        default=Decimal("0.15"), ge=0, le=1.0, description="Max total account drawdown percentage triggering halt (default 15%)"
    )
    max_leverage: Decimal = Field(
        default=Decimal("10.0"), ge=1.0, description="Maximum permitted leverage multiplier"
    )
    min_risk_reward_ratio: Decimal = Field(
        default=Decimal("1.5"), ge=0, description="Minimum required target / stop-loss reward ratio"
    )
    max_position_size_usd: Decimal = Field(
        default=Decimal("50000.00"), gt=0, description="Absolute ceiling on position size value in USD"
    )
    default_stop_loss_percent: Decimal = Field(
        default=Decimal("0.015"), ge=0, le=0.5, description="Fallback stop-loss percentage if signal omits stop-loss"
    )

    model_config = ConfigDict(frozen=True)

    def validate_policy(self) -> None:
        """Verify policy sanity limits."""
        if self.max_risk_per_trade_percent > self.max_daily_loss_percent:
            raise ValidationException("Max risk per trade cannot exceed max daily loss limit")


class RiskDecision(BaseModel):
    """Immutable result representing the outcome of a quantitative risk evaluation."""
    decision_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: RiskStatus = Field(...)
    signal_id: str = Field(...)
    reason: str | None = Field(default=None, description="Explanation for REJECTED or MODIFIED decisions")
    approved_quantity: Decimal | None = Field(default=None, ge=0)
    approved_leverage: Decimal | None = Field(default=None, ge=1.0)
    target_price: Decimal | None = Field(default=None)
    stop_loss: Decimal | None = Field(default=None)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True)


class RiskReport(BaseModel):
    """Diagnostic report capturing real-time account risk posture."""
    account_id: str = Field(...)
    total_equity: Decimal = Field(...)
    peak_equity: Decimal = Field(...)
    daily_realized_pnl: Decimal = Field(...)
    current_drawdown_percent: Decimal = Field(..., ge=0)
    daily_loss_percent: Decimal = Field(...)
    is_trading_halted: bool = Field(default=False)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(frozen=True)
