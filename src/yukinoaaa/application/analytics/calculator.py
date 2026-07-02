"""Performance Analytics Calculator using pure Decimal math (zero external dependencies)."""

from decimal import Decimal
import math
from yukinoaaa.domain.backtest.models import PerformanceMetrics, TradeRecord


class PerformanceCalculator:
    """Calculates industry-standard quantitative trading performance metrics without numpy/pandas."""

    @staticmethod
    def calculate_metrics(
        initial_equity: Decimal,
        final_equity: Decimal,
        trades: list[TradeRecord],
        equity_curve: list[Decimal],
        risk_free_rate_annual: Decimal = Decimal("0.02"),
    ) -> PerformanceMetrics:
        """Compute Sharpe, Sortino, drawdowns, win rates, and return ratios from trade logs."""
        if initial_equity <= Decimal("0"):
            initial_equity = Decimal("1.0")

        total_return_pct = ((final_equity - initial_equity) / initial_equity).quantize(Decimal("0.0001"))
        total_trades = len(trades)

        if total_trades == 0:
            return PerformanceMetrics(
                initial_equity=initial_equity,
                final_equity=final_equity,
                total_return_percentage=total_return_pct,
            )

        winning_trades = 0
        losing_trades = 0
        gross_profit = Decimal("0.0")
        gross_loss = Decimal("0.0")
        total_pnl = Decimal("0.0")
        largest_win = Decimal("0.0")
        largest_loss = Decimal("0.0")
        returns: list[Decimal] = []

        for t in trades:
            pnl = t.realized_pnl
            total_pnl += pnl
            returns.append(t.return_percentage)

            if pnl > Decimal("0"):
                winning_trades += 1
                gross_profit += pnl
                if pnl > largest_win:
                    largest_win = pnl
            elif pnl < Decimal("0"):
                losing_trades += 1
                gross_loss += abs(pnl)
                if pnl < largest_loss:
                    largest_loss = pnl

        win_rate = (Decimal(winning_trades) / Decimal(total_trades)).quantize(Decimal("0.0001"))
        avg_trade_pnl = (total_pnl / Decimal(total_trades)).quantize(Decimal("0.0001"))

        profit_factor = Decimal("0.0")
        if gross_loss > Decimal("0"):
            profit_factor = (gross_profit / gross_loss).quantize(Decimal("0.0001"))
        elif gross_profit > Decimal("0"):
            profit_factor = Decimal("999.9999")  # Infinite profit factor capped

        # Calculate Max Drawdown from Equity Curve
        max_dd_amt = Decimal("0.0")
        max_dd_pct = Decimal("0.0")
        peak = initial_equity
        for eq in equity_curve:
            if eq > peak:
                peak = eq
            dd_amt = peak - eq
            if dd_amt > max_dd_amt:
                max_dd_amt = dd_amt
            if peak > Decimal("0"):
                dd_pct = dd_amt / peak
                if dd_pct > max_dd_pct:
                    max_dd_pct = dd_pct

        # Calculate Sharpe and Sortino Ratios
        sharpe = Decimal("0.0")
        sortino = Decimal("0.0")
        if len(returns) >= 2:
            mean_return = sum(returns, Decimal("0.0")) / Decimal(len(returns))
            # Approximate per-trade risk free rate assuming 252 trading days
            rf_per_trade = risk_free_rate_annual / Decimal("252.0")
            excess_returns = [r - rf_per_trade for r in returns]
            mean_excess = sum(excess_returns, Decimal("0.0")) / Decimal(len(excess_returns))

            # Variance and standard deviation
            var_sum = sum((r - mean_return) ** 2 for r in returns)
            std_dev_val = math.sqrt(float(var_sum / Decimal(len(returns) - 1)))
            std_dev = Decimal(str(std_dev_val))

            if std_dev > Decimal("0.000001"):
                # Annualized Sharpe ratio factor approximation
                sharpe = (mean_excess / std_dev * Decimal("15.8745")).quantize(Decimal("0.0001"))  # sqrt(252) ~ 15.8745

            # Downside deviation for Sortino
            downside_sq_sum = sum((min(Decimal("0.0"), r - rf_per_trade)) ** 2 for r in returns)
            if downside_sq_sum > Decimal("0"):
                down_std_val = math.sqrt(float(downside_sq_sum / Decimal(len(returns))))
                down_std = Decimal(str(down_std_val))
                if down_std > Decimal("0.000001"):
                    sortino = (mean_excess / down_std * Decimal("15.8745")).quantize(Decimal("0.0001"))

        return PerformanceMetrics(
            initial_equity=initial_equity,
            final_equity=final_equity,
            total_return_percentage=total_return_pct,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_realized_pnl=total_pnl.quantize(Decimal("0.0001")),
            max_drawdown_amount=max_dd_amt.quantize(Decimal("0.0001")),
            max_drawdown_percentage=max_dd_pct.quantize(Decimal("0.0001")),
            profit_factor=profit_factor,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            average_trade_pnl=avg_trade_pnl,
            largest_win=largest_win.quantize(Decimal("0.0001")),
            largest_loss=largest_loss.quantize(Decimal("0.0001")),
        )
