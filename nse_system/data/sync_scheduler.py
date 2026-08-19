"""Automated Daily Incremental EOD Sync Engine."""
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
import os
import pandas as pd

from nse_system.data.historical_collector import HistoricalDataCollector
from nse_system.data.universe import UniverseManager
from nse_system.data.bhavcopy import NSEBhavcopyFetcher

class DailyDataSynchronizer:
    """Performs daily incremental update of local NSE Parquet datasets."""

    def __init__(self, data_dir: Optional[str] = None):
        self.collector = HistoricalDataCollector(data_dir=data_dir)
        self.bhav_fetcher = NSEBhavcopyFetcher()

    def sync_daily_eod(self, universe_name: str = 'fno', timeframe: str = '1d') -> Dict[str, int]:
        """Incrementally updates all symbols in universe up to today."""
        symbols = UniverseManager.get_universe(universe_name)
        today = datetime.now()
        sync_results: Dict[str, int] = {}

        for sym in symbols:
            fpath = self.collector.get_symbol_filepath(sym, timeframe)
            start_date = today - timedelta(days=5) # Default recent lookback

            if os.path.exists(fpath):
                try:
                    df = pd.read_parquet(fpath)
                    if not df.empty:
                        last_ts = df.index.max()
                        if isinstance(last_ts, pd.Timestamp):
                            last_ts = last_ts.to_pydatetime()
                        start_date = last_ts
                except Exception:
                    pass

            if (today.date() - start_date.date()).days >= 1:
                try:
                    new_df = self.collector.download_symbol(sym, start_date, today, timeframe)
                    sync_results[sym] = len(new_df)
                except Exception:
                    sync_results[sym] = 0
            else:
                sync_results[sym] = 0  # Already up to date

        return sync_results
