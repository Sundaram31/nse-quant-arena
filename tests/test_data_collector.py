"""Unit tests for Universe, Bhavcopy, Historical Collector, and Daily Sync."""
import unittest
import os
import shutil
import tempfile
from datetime import datetime, date, timedelta
from nse_system.data.universe import UniverseManager
from nse_system.data.bhavcopy import NSEBhavcopyFetcher
from nse_system.data.historical_collector import HistoricalDataCollector
from nse_system.data.sync_scheduler import DailyDataSynchronizer

class TestDataCollector(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_universe_manager(self):
        fno = UniverseManager.get_fno_symbols()
        nifty500 = UniverseManager.get_nifty_500_symbols()
        self.assertGreater(len(fno), 100)
        self.assertGreater(len(nifty500), 100)
        self.assertIn('RELIANCE', fno)
        self.assertIn('TCS', fno)
        self.assertIn('INFY', fno)

    def test_bhavcopy_fetcher(self):
        fetcher = NSEBhavcopyFetcher(download_dir=self.temp_dir)
        test_date = date(2025, 1, 15) # Wednesday
        df = fetcher.fetch_equity_bhavcopy(test_date)
        self.assertIsNotNone(df)
        self.assertFalse(df.empty)
        self.assertIn('SYMBOL', df.columns)
        self.assertIn('CLOSE_PRICE', df.columns)

    def test_historical_collector_and_datastore(self):
        collector = HistoricalDataCollector(data_dir=self.temp_dir)
        start_date = datetime.now() - timedelta(days=10)
        end_date = datetime.now()
        
        df = collector.download_symbol('RELIANCE', start_date, end_date, timeframe='1d')
        self.assertFalse(df.empty)
        self.assertGreater(len(df), 5)
        
        status_df = collector.get_datastore_status()
        self.assertFalse(status_df.empty)
        self.assertEqual(status_df['Symbol'].iloc[0], 'RELIANCE')

    def test_daily_synchronizer(self):
        sync = DailyDataSynchronizer(data_dir=self.temp_dir)
        results = sync.sync_daily_eod(universe_name='nifty50', timeframe='1d')
        self.assertGreater(len(results), 10)

if __name__ == '__main__':
    unittest.main()
