"""Tests for Risk Validator multi-layer evaluation."""

from decimal import Decimal

from yukinoaaa.application.risk.sizing import PositionCalculator
from yukinoaaa.application.risk.validator import RiskValidator
from yukinoaaa.domain.risk.models import RiskPolicy, RiskReport, RiskStatus
from yukinoaaa.domain.trading.models import OrderSide, Portfolio, TradeSignal


def _make_report(drawdown: str = "0.0", daily_loss: str = "0.0", halted: bool = False) -> RiskReport:
    return RiskReport(
        account_id="acc1",
        total_equity=Decimal("10000"),
        peak_equity=Decimal("10000"),
        daily_realized_pnl=Decimal("0"),
        current_drawdown_percent=Decimal(drawdown),
        daily_loss_percent=Decimal(daily_loss),
        is_trading_halted=halted,
    )


def test_validator_rejects_on_drawdown_and_halt() -> None:
    """Verify validator rejects signal when trading is halted or drawdown exceeds policy ceiling."""
    policy = RiskPolicy(max_drawdown_percent=Decimal("0.15"))
    validator = RiskValidator(policy, PositionCalculator())
    port = Portfolio(account_id="acc1", available_balance=Decimal("10000"))
    sig = TradeSignal(symbol="BTC/USDT", timeframe="1m", side=OrderSide.BUY, strategy_name="Test")

    dec_halt = validator.validate(sig, Decimal("100"), port, _make_report(halted=True))
    assert dec_halt.status == RiskStatus.REJECTED
    assert "halted" in str(dec_halt.reason)

    dec_dd = validator.validate(sig, Decimal("100"), port, _make_report(drawdown="0.16"))
    assert dec_dd.status == RiskStatus.REJECTED
    assert "drawdown" in str(dec_dd.reason).lower()


def test_validator_rejects_low_risk_reward_ratio() -> None:
    """Verify validator rejects trade setup when reward/risk ratio is below minimum policy requirement."""
    policy = RiskPolicy(min_risk_reward_ratio=Decimal("1.5"))
    validator = RiskValidator(policy, PositionCalculator())
    port = Portfolio(account_id="acc1", available_balance=Decimal("10000"))

    # Entry = 100, Target = 105 (reward=5), SL = 90 (risk=10) -> R:R = 0.5 < 1.5
    sig_low_rr = TradeSignal(
        symbol="BTC/USDT",
        timeframe="1m",
        side=OrderSide.BUY,
        strategy_name="Test",
        target_price=Decimal("105.0"),
        stop_loss=Decimal("90.0"),
    )
    dec = validator.validate(sig_low_rr, Decimal("100.0"), port, _make_report())
    assert dec.status == RiskStatus.REJECTED
    assert "Risk/Reward ratio" in str(dec.reason)


def test_validator_modifies_quantity_on_balance_ceiling() -> None:
    """Verify validator returns MODIFIED status and scaled-down volume when balance is lower than required margin."""
    policy = RiskPolicy(max_risk_per_trade_percent=Decimal("0.50"), max_position_size_usd=Decimal("100000"))
    validator = RiskValidator(policy, PositionCalculator())
    # Equity = 10,000 -> Risk Amount = 5,000. Entry = 100, SL = 90 -> Dist = 10. Raw Qty = 500. Margin required = 50,000.
    # But Available Balance is only 1,000 -> Max affordable Qty = 1,000 / 100 = 10.0
    port = Portfolio(account_id="acc1", available_balance=Decimal("1000.00"))
    sig = TradeSignal(
        symbol="ETH/USDT",
        timeframe="1m",
        side=OrderSide.BUY,
        strategy_name="Test",
        target_price=Decimal("150.0"),
        stop_loss=Decimal("90.0"),
    )

    dec = validator.validate(sig, Decimal("100.0"), port, _make_report())
    assert dec.status == RiskStatus.MODIFIED
    assert dec.approved_quantity == Decimal("10.000000")
