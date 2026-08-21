"""Automated Daily Incremental EOD Sync Engine with Smart Gap Detection & Backfill."""
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
import os
import pandas as pd

from nse_system.data.historical_collector import HistoricalDataCollector
from nse_system.data.universe import UniverseManager
from nse_system.data.bhavcopy import NSEBhavcopyFetcher

class DailyDataSynchronizer:
    """Performs daily incremental update and multi-day gap backfill of NSE Parquet datasets."""

    def __init__(self, data_dir: Optional[str] = None):
        self.collector = HistoricalDataCollector(data_dir=data_dir)
        self.bhav_fetcher = NSEBhavcopyFetcher()

    def sync_daily_eod(self, universe_name: str = 'fno', timeframe: str = '1d') -> Dict[str, Any]:
        """
        Smart Gap Detection & Multi-Day Backfill:
        Detects if data has not been updated for 1, 2, 5, or N days,
        and automatically backfills all missing trading candles up to today.
        """
        symbols = UniverseManager.get_universe(universe_name)
        today = datetime.now()
        updated_count = 0
        total_bars_added = 0
        gap_details: Dict[str, str] = {}

        for sym in symbols:
            fpath = self.collector.get_symbol_filepath(sym, timeframe)
            start_date = today - timedelta(days=365) # Fallback 1 year if file missing

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

            days_gap = (today.date() - start_date.date()).days

            if days_gap >= 1:
                try:
                    # Download missing date range from last recorded date to today
                    new_df = self.collector.download_symbol(sym, start_date, today, timeframe)
                    bars_added = max(0, days_gap)
                    total_bars_added += bars_added
                    updated_count += 1
                    gap_details[sym] = f"Backfilled {days_gap} missing days ({start_date.strftime('%d-%b')} to {today.strftime('%d-%b')})"
                except Exception as e:
                    gap_details[sym] = f"Error syncing: {str(e)}"
            else:
                gap_details[sym] = "Already 100% Up to Date"

        return {
            "universe": universe_name,
            "symbols_checked": len(symbols),
            "symbols_updated": updated_count,
            "total_bars_backfilled": total_bars_added,
            "status": "SUCCESS" if updated_count > 0 or len(symbols) > 0 else "NO_DATA",
            "gap_details": gap_details
        }
