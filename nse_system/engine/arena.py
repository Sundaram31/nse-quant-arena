"""Strategy Battle Arena - Automated Multi-Strategy Tournament & Adaptive Strategy Selector."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd

from nse_system.core.models import Candle, StrategyPerformance, RegimeState
from nse_system.data.historical import NSEHistoricalDataProvider
from nse_system.data.fii_dii import FIIDIIDataProvider
from nse_system.data.options_data import OptionsDataProvider
from nse_system.engine.regime import MarketRegimeClassifier
from nse_system.engine.backtest import BacktestEngine
from nse_system.strategies import STRATEGY_REGISTRY, get_strategy

@dataclass
class ArenaTournamentResult:
    """Complete results of a multi-strategy tournament on the present market."""
    symbol: str
    timeframe: str
    test_period_days: int
    regime_state: RegimeState
    leaderboard: List[StrategyPerformance]
    winning_strategy: StrategyPerformance
    recommended_active_strategies: List[str]
    avoid_strategies: List[str]
    executive_summary: str

class StrategyBattleArena:
    """Runs automated multi-strategy arena battle to select the winning strategy for the active market regime."""

    def __init__(self, data_provider: Optional[NSEHistoricalDataProvider] = None):
        self.data_provider = data_provider or NSEHistoricalDataProvider()
        self.regime_classifier = MarketRegimeClassifier()

    def run_tournament(
        self,
        symbol: str = 'NIFTY 50',
        timeframe: str = '5m',
        days: int = 30,
        initial_capital: float = 100000.0,
        vix_level: float = 14.5
    ) -> ArenaTournamentResult:
        """Executes full strategy arena battle across all registered strategies."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # 1. Fetch market candles
        candles = self.data_provider.get_historical_candles(symbol, start_date, end_date, timeframe)
        df_candles = self.data_provider.get_historical_dataframe(symbol, start_date, end_date, timeframe)

        # 2. Classify present market regime
        regime = self.regime_classifier.classify_market(
            symbol=symbol,
            df_candles=df_candles,
            current_vix=vix_level
        )

        # 3. Battle Arena: Test all strategies
        performances: List[StrategyPerformance] = []

        for strat_name in STRATEGY_REGISTRY.keys():
            strat_instance = get_strategy(strat_name, symbol=symbol, timeframe=timeframe)
            engine = BacktestEngine(strategy=strat_instance, initial_capital=initial_capital)
            perf = engine.run(candles)
            
            # Regime synergy bonus / penalty
            if strat_name in regime.recommended_strategies:
                perf.alpha_score += 15.0  # Regime synergy bonus
            else:
                perf.alpha_score -= 10.0  # Mismatch penalty
            perf.alpha_score = round(perf.alpha_score, 2)

            performances.append(perf)

        # 4. Sort leaderboard by composite Alpha Score
        leaderboard = sorted(performances, key=lambda x: x.alpha_score, reverse=True)
        winner = leaderboard[0]

        # 5. Classify recommendations
        recommended = [p.strategy_name for p in leaderboard if p.alpha_score > 40.0 and p.net_pnl > 0]
        if not recommended:
            recommended = [winner.strategy_name]

        avoid = [p.strategy_name for p in leaderboard if p.alpha_score < 20.0 or p.net_pnl < 0]

        summary = (
            f'Market Regime detected as {regime.regime_type.value} (VIX: {vix_level:.1f}, FII Bias: {regime.fii_sentiment}, PCR: {regime.pcr_level:.2f}). '
            f'The #1 Winning Strategy for {symbol} is "{winner.strategy_name}" with Win Rate {winner.win_rate:.1f}%, '
            f'Profit Factor {winner.profit_factor:.2f}, and Net PnL ₹{winner.net_pnl:,.2f} after Indian taxes.'
        )

        return ArenaTournamentResult(
            symbol=symbol,
            timeframe=timeframe,
            test_period_days=days,
            regime_state=regime,
            leaderboard=leaderboard,
            winning_strategy=winner,
            recommended_active_strategies=recommended,
            avoid_strategies=avoid,
            executive_summary=summary
        )

    # Alias for flexibility across CLI, API, and UI harnesses
    run_arena = run_tournament
