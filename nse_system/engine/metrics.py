"""Quant Performance Metrics & Alpha Scoring Engine."""
from typing import List, Dict, Any
import numpy as np
import pandas as pd
from nse_system.core.models import Trade, StrategyPerformance

class QuantMetricsCalculator:
    """Calculates hedge-fund grade performance and risk metrics."""

    @classmethod
    def calculate_performance(
        cls,
        strategy_name: str,
        symbol: str,
        trades: List[Trade],
        initial_capital: float = 100000.0,
        equity_curve: List[Dict[str, Any]] = None
    ) -> StrategyPerformance:
        """Compute full performance report from closed trades."""
        total_trades = len(trades)
        if total_trades == 0:
            return StrategyPerformance(
                strategy_name=strategy_name,
                symbol=symbol,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                profit_factor=0.0,
                gross_pnl=0.0,
                total_taxes=0.0,
                net_pnl=0.0,
                roi_pct=0.0,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                max_drawdown_pct=0.0,
                max_drawdown_duration_days=0.0,
                calmar_ratio=0.0,
                expectancy=0.0,
                alpha_score=0.0,
                trades=[]
            )

        wins = [t for t in trades if t.net_pnl > 0]
        losses = [t for t in trades if t.net_pnl <= 0]
        winning_trades = len(wins)
        losing_trades = len(losses)
        win_rate = (winning_trades / total_trades) * 100.0

        total_gain = sum(t.net_pnl for t in wins)
        total_loss = abs(sum(t.net_pnl for t in losses))
        profit_factor = (total_gain / total_loss) if total_loss > 0 else (99.0 if total_gain > 0 else 0.0)

        gross_pnl = sum(t.gross_pnl for t in trades)
        total_taxes = sum(t.taxes for t in trades)
        net_pnl = sum(t.net_pnl for t in trades)
        roi_pct = (net_pnl / initial_capital) * 100.0

        avg_win = (total_gain / winning_trades) if winning_trades > 0 else 0.0
        avg_loss = (total_loss / losing_trades) if losing_trades > 0 else 0.0
        expectancy = ((win_rate / 100.0) * avg_win) - (((100.0 - win_rate) / 100.0) * avg_loss)

        # Returns series & Sharpe / Sortino
        pnls = np.array([t.net_pnl / initial_capital for t in trades])
        mean_ret = np.mean(pnls) if len(pnls) > 0 else 0.0
        std_ret = np.std(pnls) if len(pnls) > 1 else 0.001
        downside_std = np.std(pnls[pnls < 0]) if len(pnls[pnls < 0]) > 1 else 0.001

        # Annualized Sharpe (assuming ~250 trading days)
        ann_factor = np.sqrt(min(250, total_trades))
        sharpe = (mean_ret / (std_ret + 1e-6)) * ann_factor
        sortino = (mean_ret / (downside_std + 1e-6)) * ann_factor

        # Drawdown calculation
        cum_equity = initial_capital + np.cumsum([t.net_pnl for t in trades])
        cum_max = np.maximum.accumulate(cum_equity)
        drawdowns = (cum_max - cum_equity) / cum_max
        max_dd_pct = float(np.max(drawdowns)) * 100.0 if len(drawdowns) > 0 else 0.0

        calmar = (roi_pct / max_dd_pct) if max_dd_pct > 0 else (roi_pct if roi_pct > 0 else 0.0)

        # Composite Alpha Score for Leaderboard Ranking
        # Higher win rate, profit factor, sharpe, lower drawdown
        norm_pf = min(5.0, profit_factor) / 5.0
        norm_wr = win_rate / 100.0
        norm_sharpe = np.clip(sharpe / 3.0, -1.0, 1.0)
        dd_penalty = min(1.0, max_dd_pct / 20.0)
        roi_norm = np.clip(roi_pct / 50.0, -1.0, 1.0)

        alpha_score = (
            0.25 * norm_wr +
            0.25 * norm_pf +
            0.20 * norm_sharpe +
            0.20 * roi_norm -
            0.20 * dd_penalty
        ) * 100.0

        return StrategyPerformance(
            strategy_name=strategy_name,
            symbol=symbol,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=round(win_rate, 2),
            profit_factor=round(profit_factor, 2),
            gross_pnl=round(gross_pnl, 2),
            total_taxes=round(total_taxes, 2),
            net_pnl=round(net_pnl, 2),
            roi_pct=round(roi_pct, 2),
            sharpe_ratio=round(float(sharpe), 2),
            sortino_ratio=round(float(sortino), 2),
            max_drawdown_pct=round(max_dd_pct, 2),
            max_drawdown_duration_days=0.0,
            calmar_ratio=round(calmar, 2),
            expectancy=round(expectancy, 2),
            alpha_score=round(float(alpha_score), 2),
            trades=trades
        )
