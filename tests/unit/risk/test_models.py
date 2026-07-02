"""Tests for risk domain models and policy validation."""

from decimal import Decimal
import pytest
from yukinoaaa.domain.exceptions import ValidationException
from yukinoaaa.domain.risk.models import RiskDecision, RiskPolicy, RiskReport, RiskStatus


def test_risk_policy_validation_and_defaults() -> None:
    """Verify RiskPolicy defaults and validation checks."""
    policy = RiskPolicy()
    assert policy.max_risk_per_trade_percent == Decimal("0.02")
    assert policy.max_drawdown_percent == Decimal("0.15")
    policy.validate_policy()

    with pytest.raises(ValidationException):
        invalid_policy = RiskPolicy(max_risk_per_trade_percent=Decimal("0.10"), max_daily_loss_percent=Decimal("0.05"))
        invalid_policy.validate_policy()


def test_risk_decision_and_report_immutability() -> None:
    """Verify RiskDecision and RiskReport models are frozen objects."""
    dec = RiskDecision(status=RiskStatus.APPROVED, signal_id="sig_001", approved_quantity=Decimal("1.5"))
    assert dec.status == RiskStatus.APPROVED

    with pytest.raises(Exception):
        dec.status = RiskStatus.REJECTED  # type: ignore

    report = RiskReport(
        account_id="acc_test",
        total_equity=Decimal("10000"),
        peak_equity=Decimal("12000"),
        daily_realized_pnl=Decimal("-500"),
        current_drawdown_percent=Decimal("0.166666"),
        daily_loss_percent=Decimal("0.041666"),
    )
    assert report.current_drawdown_percent > Decimal("0.15")
