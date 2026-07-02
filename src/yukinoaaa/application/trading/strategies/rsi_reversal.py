"""RSI Reversal trading strategy plugin implementation."""

from decimal import Decimal
from typing import Any

from yukinoaaa.application.interfaces.strategy import IStrategy
from yukinoaaa.domain.market.models import MarketSnapshot
from yukinoaaa.domain.trading.models import OrderSide, TradeSignal


class RsiReversalStrategy(IStrategy):
    """Generates BUY signal when RSI < oversold_threshold and SELL signal when RSI > overbought_threshold."""

    def __init__(
        self,
        symbol: str = "BTC/USDT",
        timeframe: str = "1m",
        rsi_indicator_name: str = "RSI_14",
        oversold_threshold: float = 30.0,
        overbought_threshold: float = 70.0,
    ) -> None:
        """Initialize RSI thresholds and target market."""
        self._symbol = symbol.strip().upper()
        self._timeframe = timeframe.strip().lower()
        self._rsi_name = rsi_indicator_name
        self._oversold = Decimal(str(oversold_threshold))
        self._overbought = Decimal(str(overbought_threshold))
        self._last_signal_side: OrderSide | None = None

    @property
    def name(self) -> str:
        return f"RSI_Reversal_{self._rsi_name}"

    @property
    def symbol(self) -> str:
        return self._symbol

    @property
    def timeframe(self) -> str:
        return self._timeframe

    def on_indicator_updated(self, indicator_name: str, values: dict[str, Any]) -> TradeSignal | None:
        """Check if updated indicator is RSI and evaluate reversal thresholds."""
        if indicator_name != self._rsi_name:
            return None

        val_str = values.get("rsi") or values.get("value")
        if not val_str:
            return None

        try:
            rsi_val = Decimal(str(val_str))
            if rsi_val <= self._oversold and self._last_signal_side != OrderSide.BUY:
                self._last_signal_side = OrderSide.BUY
                return TradeSignal(
                    symbol=self.symbol,
                    timeframe=self.timeframe,
                    side=OrderSide.BUY,
                    strategy_name=self.name,
                    confidence=0.85,
                    metadata={"rsi": str(rsi_val)},
                )
            elif rsi_val >= self._overbought and self._last_signal_side != OrderSide.SELL:
                self._last_signal_side = OrderSide.SELL
                return TradeSignal(
                    symbol=self.symbol,
                    timeframe=self.timeframe,
                    side=OrderSide.SELL,
                    strategy_name=self.name,
                    confidence=0.85,
                    metadata={"rsi": str(rsi_val)},
                )
        except Exception:
            return None

        return None

    def on_market_snapshot(self, snapshot: MarketSnapshot) -> TradeSignal | None:
        """Not used in pure RSI reversal logic."""
        return None
