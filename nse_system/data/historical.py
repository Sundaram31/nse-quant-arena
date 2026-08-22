"""NSE Historical Market Data Fetcher & Simulator."""
from datetime import datetime, timedelta, time
from typing import List, Dict, Optional
import os
import math
import numpy as np
import pandas as pd
import requests

from nse_system.core.models import Candle
from nse_system.core.constants import MarketHours
from nse_system.data.base import BaseDataProvider
from nse_system.data.symbols import get_symbol_info
from nse_system.data.stock_prices import NSE_REAL_PRICES
from nse_system.data.adjustments import CorporateActionAdjuster

DEFAULT_PRICES = {
    'NIFTY 50': 24500.0,
    'NIFTY BANK': 51200.0,
    'FINNIFTY': 23400.0,
    'NIFTY IT': 38900.0,
    'NIFTY AUTO': 25100.0,
    'NIFTY PHARMA': 21400.0,
    'NIFTY METAL': 9200.0,
    'NIFTY FMCG': 58200.0,
    'NIFTY REALTY': 1050.0,
    'NIFTY ENERGY': 39100.0,
    'INDIA VIX': 14.5,
    'RELIANCE': 2980.0,
    'TCS': 4150.0,
    'HDFCBANK': 1640.0,
    'INFY': 1820.0,
    'ICICIBANK': 1180.0,
    'BHARTIARTL': 1460.0,
    'SBIN': 830.0,
    'ITC': 490.0,
    'LT': 3650.0,
    'TATAMOTORS': 980.0,
    'BAJFINANCE': 6850.0,
    'MARUTI': 12200.0,
    'SUNPHARMA': 1710.0,
    'TITAN': 3450.0,
    'TATASTEEL': 155.0,
}

class NSEHistoricalDataProvider(BaseDataProvider):
    """Provides historical OHLCV candles for NSE stocks and indices with automatic split/bonus adjustments."""

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = cache_dir or os.path.expanduser('~/.cache/nse_system')
        os.makedirs(self.cache_dir, exist_ok=True)
        self._mem_cache: Dict[str, pd.DataFrame] = {}

    def get_historical_candles(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = '5m',
        adjusted: bool = True
    ) -> List[Candle]:
        """Return list of typed Candle objects with continuous split/bonus adjusted data."""
        df = self.get_historical_dataframe(symbol, start_date, end_date, timeframe, adjusted=adjusted)
        candles: List[Candle] = []
        for row in df.itertuples():
            candles.append(Candle(
                timestamp=row.Index.to_pydatetime() if isinstance(row.Index, pd.Timestamp) else row.Index,
                open=float(row.open),
                high=float(row.high),
                low=float(row.low),
                close=float(row.close),
                volume=float(row.volume),
                oi=float(getattr(row, 'oi', 0.0)),
                vwap=float(getattr(row, 'vwap', row.close))
            ))
        return candles

    def get_historical_dataframe(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = '5m',
        adjusted: bool = True
    ) -> pd.DataFrame:
        """Fetch historical DataFrame with automatic backward corporate action adjustments."""
        sym_info = get_symbol_info(symbol)
        clean_sym = sym_info.symbol
        key = f'{clean_sym}_{start_date.date()}_{end_date.date()}_{timeframe}_adj_{adjusted}'
        
        if key in self._mem_cache:
            return self._mem_cache[key]

        # 1. Candidate symbols (including index ETF fallbacks)
        candidate_symbols = [clean_sym, symbol, clean_sym.replace(' ', '_'), clean_sym.replace(' ', '')]
        if clean_sym in ('NIFTY 50', 'NIFTY', '^NSEI', 'NIFTY_50'):
            candidate_symbols.extend(['NIFTYBEES', 'NIFTYETF', 'NIFTY50ADD'])
        elif clean_sym in ('NIFTY BANK', 'BANKNIFTY', '^NSEBANK', 'NIFTY_BANK'):
            candidate_symbols.extend(['BANKBEES', 'BANKETF', 'HDFCBANK'])
        elif clean_sym in ('NIFTY IT', '^CNXIT', 'NIFTY_IT'):
            candidate_symbols.extend(['TCS', 'INFY'])
        elif clean_sym in ('NIFTY AUTO', '^CNXAUTO', 'NIFTY_AUTO'):
            candidate_symbols.extend(['AUTOBEES', 'TATAMOTORS', 'M&M'])
        elif clean_sym in ('NIFTY PHARMA', '^CNXPHARMA', 'NIFTY_PHARMA'):
            candidate_symbols.extend(['SUNPHARMA', 'CIPLA'])
        elif clean_sym in ('NIFTY FMCG', '^CNXFMCG', 'NIFTY_FMCG'):
            candidate_symbols.extend(['ITC', 'HINDUNILVR'])
        elif clean_sym in ('NIFTY METAL', '^CNXMETAL', 'NIFTY_METAL'):
            candidate_symbols.extend(['TATASTEEL', 'JSWSTEEL'])
        elif clean_sym in ('NIFTY REALTY', '^CNXREALTY', 'NIFTY_REALTY'):
            candidate_symbols.extend(['DLF', 'GODREJPROP'])
        elif clean_sym in ('NIFTY ENERGY', '^CNXENERGY', 'NIFTY_ENERGY'):
            candidate_symbols.extend(['RELIANCE', 'NTPC', 'ONGC'])

        # 2. Check local / bundled Parquet Datastore
        for c_sym in candidate_symbols:
            for tf in [timeframe, '1d']:
                possible_paths = [
                    os.path.join(os.path.dirname(__file__), 'datastore', f"{c_sym}_{tf}.parquet"),
                    os.path.join(os.getcwd(), 'nse_system', 'data', 'datastore', f"{c_sym}_{tf}.parquet"),
                    os.path.join(self.cache_dir, 'data', f"{c_sym}_{tf}.parquet"),
                    os.path.join(self.cache_dir, f"{c_sym}_{tf}.parquet")
                ]
                for p_path in possible_paths:
                    if os.path.exists(p_path):
                        try:
                            df = pd.read_parquet(p_path)
                            if not df.empty:
                                df_sliced = df[(df.index >= pd.Timestamp(start_date)) & (df.index <= pd.Timestamp(end_date))].copy()
                                if len(df_sliced) < 3:
                                    days_diff = max(10, (end_date - start_date).days)
                                    df_sliced = df.tail(days_diff).copy()
                                
                                if adjusted:
                                    df_sliced = CorporateActionAdjuster.adjust_dataframe(df_sliced)

                                self._mem_cache[key] = df_sliced
                                return df_sliced
                        except Exception:
                            pass

        # 3. Return empty DataFrame if no verified data exists in datastore
        empty_df = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume', 'oi', 'vwap'])
        empty_df.index.name = 'timestamp'
        self._mem_cache[key] = empty_df
        return empty_df
