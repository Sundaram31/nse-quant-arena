"""Unit tests for FII/DII, Options OI, Volatility, and RRG analytics."""
import unittest
import pandas as pd
import numpy as np
from nse_system.data.fii_dii import FIIDIIDataProvider
from nse_system.data.options_data import OptionsDataProvider
from nse_system.analytics.options_oi import OptionsOIAnalyzer
from nse_system.analytics.volatility import VolatilityEngine
from nse_system.analytics.rrg import RRGAnalyzer

class TestAnalytics(unittest.TestCase):

    def test_fii_dii_analytics(self):
        provider = FIIDIIDataProvider()
        latest = provider.get_latest_fii_dii_data()
        self.assertIsNotNone(latest.fii_cash_net)
        self.assertIn(latest.institutional_bias, ['BULLISH', 'BEARISH', 'NEUTRAL'])
        score = provider.get_fii_sentiment_score()
        self.assertTrue(-1.0 <= score <= 1.0)

    def test_options_chain_and_max_pain(self):
        provider = OptionsDataProvider()
        chain = provider.get_options_chain('NIFTY 50', spot_price=24500.0, atm_iv=14.0)
        self.assertEqual(chain.underlying, 'NIFTY 50')
        self.assertGreater(chain.pcr_oi, 0.0)
        self.assertGreater(chain.max_pain, 20000.0)
        self.assertGreater(len(chain.contracts), 10)

        analysis = OptionsOIAnalyzer.analyze_chain(chain)
        self.assertIn('pcr_status', analysis)
        self.assertIn('resistance_1', analysis)

    def test_volatility_and_greeks(self):
        vix_info = VolatilityEngine.analyze_india_vix(15.5)
        self.assertEqual(vix_info.regime, 'NORMAL')
        self.assertGreater(len(vix_info.suitable_strategies), 0)

        # Greeks
        greeks = VolatilityEngine.calculate_greeks(spot=24500, strike=24500, t_years=0.08, r=0.07, iv=0.15, option_type='CE')
        self.assertAlmostEqual(greeks['delta'], 0.5, delta=0.15)
        self.assertGreater(greeks['vega'], 0.0)

    def test_rrg_quadrants(self):
        rrg = RRGAnalyzer(ratio_period=5, momentum_period=5)
        dates = pd.date_range('2025-01-01', periods=30)
        bench = pd.Series(np.linspace(100, 110, 30), index=dates)
        asset1 = pd.Series(np.linspace(100, 120, 30), index=dates) # Outperforming
        asset2 = pd.Series(np.linspace(100, 95, 30), index=dates)  # Underperforming

        results = rrg.calculate_rrg({'WINNER': asset1, 'LOSER': asset2}, bench)
        self.assertIn('WINNER', results)
        self.assertIn('LOSER', results)
        self.assertEqual(results['WINNER'].quadrant.value, 'LEADING')

if __name__ == '__main__':
    unittest.main()
