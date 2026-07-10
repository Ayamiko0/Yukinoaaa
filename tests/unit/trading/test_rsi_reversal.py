"""Tests for RSI Reversal strategy plugin."""

from yukinoaaa.application.trading.strategies.rsi_reversal import RsiReversalStrategy
from yukinoaaa.domain.trading.models import OrderSide


def test_rsi_reversal_threshold_evaluation() -> None:
    """Verify strategy emits BUY on oversold, SELL on overbought, and suppresses immediate duplicates."""
    strat = RsiReversalStrategy(
        symbol="ETH/USDT", timeframe="5m", oversold_threshold=30.0, overbought_threshold=70.0
    )
    assert strat.name == "RSI_Reversal_RSI_14"

    # Normal RSI = 50 -> no signal
    sig_normal = strat.on_indicator_updated("RSI_14", {"rsi": "50.0"})
    assert sig_normal is None

    # Oversold RSI = 28 -> BUY signal
    sig_buy = strat.on_indicator_updated("RSI_14", {"rsi": "28.0"})
    assert sig_buy is not None
    assert sig_buy.side == OrderSide.BUY

    # Still oversold RSI = 25 -> duplicate suppressed
    sig_dup = strat.on_indicator_updated("RSI_14", {"rsi": "25.0"})
    assert sig_dup is None

    # Overbought RSI = 75 -> SELL signal
    sig_sell = strat.on_indicator_updated("RSI_14", {"rsi": "75.0"})
    assert sig_sell is not None
    assert sig_sell.side == OrderSide.SELL
