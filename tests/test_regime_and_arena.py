"""Unit tests for Market Regime and Strategy Battle Arena."""
import unittest
from nse_system.engine.arena import StrategyBattleArena
from nse_system.data.historical import NSEHistoricalDataProvider

class TestRegimeAndArena(unittest.TestCase):

    def test_tournament_execution(self):
        arena = StrategyBattleArena()
        result = arena.run_tournament(
            symbol='NIFTY 50',
            timeframe='15m',
            days=15,
            initial_capital=100000.0,
            vix_level=14.0
        )
        self.assertEqual(result.symbol, 'NIFTY 50')
        self.assertIsNotNone(result.regime_state)
        self.assertGreater(len(result.leaderboard), 3)
        self.assertIsNotNone(result.winning_strategy)
        self.assertGreater(len(result.recommended_active_strategies), 0)
        self.assertTrue(len(result.executive_summary) > 10)

if __name__ == '__main__':
    unittest.main()
