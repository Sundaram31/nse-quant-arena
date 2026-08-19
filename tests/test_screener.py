"""Unit tests for Multi-Factor Quant Stock Screener."""
import unittest
from nse_system.analytics.screener import QuantStockScreener, TradingType

class TestQuantScreener(unittest.TestCase):

    def setUp(self):
        self.screener = QuantStockScreener()

    def test_screener_execution(self):
        candidates = self.screener.scan_universe(universe_name='fno', min_confidence=50.0)
        self.assertIsInstance(candidates, list)
        self.assertGreater(len(candidates), 0)

        for c in candidates:
            self.assertIn(c.trading_type, [
                TradingType.SWING_LONG, TradingType.SWING_SHORT,
                TradingType.INTRADAY_LONG, TradingType.INTRADAY_SHORT
            ])
            self.assertGreater(c.confidence_score, 0)
            self.assertGreater(c.entry_trigger, 0)
            self.assertGreater(c.stop_loss, 0)
            self.assertGreater(c.target_1, 0)

            # Check Risk-Reward Direction
            if c.trading_type in (TradingType.SWING_LONG, TradingType.INTRADAY_LONG):
                self.assertGreater(c.target_1, c.entry_trigger)
                self.assertLess(c.stop_loss, c.entry_trigger)
            else:
                self.assertLess(c.target_1, c.entry_trigger)
                self.assertGreater(c.stop_loss, c.entry_trigger)

if __name__ == '__main__':
    unittest.main()
