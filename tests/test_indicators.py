"""Unit tests for Technical Indicators and Pivots."""
import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from nse_system.indicators.technical import ema, sma, rsi, atr, supertrend, vwap, bollinger_bands
from nse_system.indicators.pivots import PivotEngine

class TestIndicators(unittest.TestCase):

    def setUp(self):
        np.random.seed(42)
        dates = [datetime(2025, 1, 1, 9, 15) + timedelta(minutes=5*i) for i in range(100)]
        prices = 1000.0 + np.cumsum(np.random.normal(0.1, 2.0, 100))
        self.df = pd.DataFrame({
            'open': prices - 1.0,
            'high': prices + 3.0,
            'low': prices - 3.0,
            'close': prices,
            'volume': np.random.randint(100, 1000, 100)
        }, index=dates)

    def test_ema_and_sma(self):
        e20 = ema(self.df['close'], 20)
        s20 = sma(self.df['close'], 20)
        self.assertEqual(len(e20), 100)
        self.assertEqual(len(s20), 100)

    def test_rsi(self):
        r = rsi(self.df['close'], 14)
        self.assertTrue(r.min() >= 0.0)
        self.assertTrue(r.max() <= 100.0)

    def test_supertrend(self):
        st_df = supertrend(self.df, 10, 3.0)
        self.assertIn('supertrend', st_df.columns)
        self.assertIn('supertrend_direction', st_df.columns)
        self.assertTrue(set(st_df['supertrend_direction'].unique()).issubset({-1, 1}))

    def test_vwap(self):
        v_df = vwap(self.df)
        self.assertIn('vwap', v_df.columns)
        self.assertIn('vwap_sd1_upper', v_df.columns)
        self.assertTrue((v_df['vwap_sd1_upper'] >= v_df['vwap']).all())

    def test_cpr_engine(self):
        cpr = PivotEngine.calculate_daily_cpr(high=24500.0, low=24200.0, close=24400.0)
        self.assertAlmostEqual(cpr.pivot, 24366.67, places=1)
        self.assertGreater(cpr.r1, cpr.pivot)
        self.assertLess(cpr.s1, cpr.pivot)

if __name__ == '__main__':
    unittest.main()
