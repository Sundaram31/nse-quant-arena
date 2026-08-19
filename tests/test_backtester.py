"""Unit tests for Backtesting Engine and RMS."""
import unittest
from datetime import datetime, timedelta
from nse_system.data.historical import NSEHistoricalDataProvider
from nse_system.strategies.vwap_supertrend import VWAPSuperTrendStrategy
from nse_system.strategies.orb import ORBStrategy
from nse_system.engine.backtest import BacktestEngine

class TestBacktester(unittest.TestCase):

    def test_backtest_vwap_supertrend(self):
        dp = NSEHistoricalDataProvider()
        candles = dp.get_historical_candles('RELIANCE', datetime.now() - timedelta(days=10), datetime.now(), '5m')
        strat = VWAPSuperTrendStrategy(symbol='RELIANCE', timeframe='5m')
        engine = BacktestEngine(strategy=strat, initial_capital=100000.0)
        perf = engine.run(candles)

        self.assertEqual(perf.symbol, 'RELIANCE')
        self.assertIsInstance(perf.win_rate, float)
        self.assertIsInstance(perf.net_pnl, float)
        self.assertGreaterEqual(perf.total_trades, 0)

    def test_backtest_orb(self):
        dp = NSEHistoricalDataProvider()
        candles = dp.get_historical_candles('NIFTY 50', datetime.now() - timedelta(days=10), datetime.now(), '5m')
        strat = ORBStrategy(symbol='NIFTY 50', timeframe='5m')
        engine = BacktestEngine(strategy=strat, initial_capital=100000.0)
        perf = engine.run(candles)

        self.assertEqual(perf.symbol, 'NIFTY 50')

if __name__ == '__main__':
    unittest.main()
