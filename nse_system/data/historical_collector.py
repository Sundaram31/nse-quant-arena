"""Multi-Asset Historical Data Ingestion & Parquet Datastore Engine."""
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
import os
import concurrent.futures
import pandas as pd
import numpy as np

from nse_system.data.universe import UniverseManager
from nse_system.data.historical import NSEHistoricalDataProvider
from nse_system.data.symbols import get_symbol_info

class HistoricalDataCollector:
    """Downloads, compiles, and stores historical market data for NIFTY 500 and F&O universes."""

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = data_dir or os.path.expanduser('~/.cache/nse_system/data')
        os.makedirs(self.data_dir, exist_ok=True)
        self.provider = NSEHistoricalDataProvider(cache_dir=self.data_dir)

    def get_symbol_filepath(self, symbol: str, timeframe: str = '1d') -> str:
        clean_sym = symbol.upper().replace('.NS', '').replace('^', '').replace(' ', '_')
        return os.path.join(self.data_dir, f'{clean_sym}_{timeframe}.parquet')

    def download_symbol(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = '1d'
    ) -> pd.DataFrame:
        """Downloads historical data for a single symbol and saves to Parquet."""
        fpath = self.get_symbol_filepath(symbol, timeframe)
        
        # If file exists, load and merge
        existing_df = None
        if os.path.exists(fpath):
            try:
                existing_df = pd.read_parquet(fpath)
            except Exception:
                existing_df = None

        new_df = self.provider.get_historical_dataframe(symbol, start_date, end_date, timeframe)

        if existing_df is not None and not existing_df.empty:
            merged_df = pd.concat([existing_df, new_df])
            merged_df = merged_df[~merged_df.index.duplicated(keep='last')]
            merged_df.sort_index(inplace=True)
        else:
            merged_df = new_df

        merged_df.to_parquet(fpath, compression='snappy')
        return merged_df

    def download_universe(
        self,
        universe_name: str = 'fno',
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        timeframe: str = '1d',
        max_workers: int = 8,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, int]:
        """Downloads full universe (NIFTY 500, F&O) in parallel."""
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            # Default 5 years for 1d, 60 days for intraday
            days_back = 1825 if timeframe == '1d' else 60
            start_date = end_date - timedelta(days=days_back)

        symbols = UniverseManager.get_universe(universe_name)
        results: Dict[str, int] = {}

        def _worker(sym):
            try:
                df = self.download_symbol(sym, start_date, end_date, timeframe)
                return sym, len(df)
            except Exception as e:
                return sym, -1

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_sym = {executor.submit(_worker, sym): sym for sym in symbols}
            completed = 0
            for future in concurrent.futures.as_completed(future_to_sym):
                sym, count = future.result()
                results[sym] = count
                completed += 1
                if progress_callback:
                    progress_callback(completed, len(symbols), sym, count)

        return results

    def get_datastore_status(self) -> pd.DataFrame:
        """Returns summary of all locally stored datasets."""
        records = []
        if not os.path.exists(self.data_dir):
            return pd.DataFrame()

        for fname in os.listdir(self.data_dir):
            if fname.endswith('.parquet'):
                fpath = os.path.join(self.data_dir, fname)
                try:
                    df = pd.read_parquet(fpath)
                    parts = fname.replace('.parquet', '').split('_')
                    tf = parts[-1]
                    sym = '_'.join(parts[:-1])
                    size_kb = os.path.getsize(fpath) / 1024.0

                    records.append({
                        'Symbol': sym,
                        'Timeframe': tf,
                        'Total Bars': len(df),
                        'Start Date': df.index.min().strftime('%Y-%m-%d %H:%M') if not df.empty else 'N/A',
                        'End Date': df.index.max().strftime('%Y-%m-%d %H:%M') if not df.empty else 'N/A',
                        'File Size (KB)': round(size_kb, 1),
                        'Last Close': round(float(df['close'].iloc[-1]), 2) if not df.empty else 0.0
                    })
                except Exception:
                    pass

        return pd.DataFrame(records)
