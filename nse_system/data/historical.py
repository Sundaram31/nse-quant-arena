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
    """Provides historical OHLCV candles for NSE stocks and indices."""

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = cache_dir or os.path.expanduser('~/.cache/nse_system')
        os.makedirs(self.cache_dir, exist_ok=True)
        self._mem_cache: Dict[str, pd.DataFrame] = {}

    def get_historical_candles(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = '5m'
    ) -> List[Candle]:
        """Return list of typed Candle objects."""
        df = self.get_historical_dataframe(symbol, start_date, end_date, timeframe)
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
        timeframe: str = '5m'
    ) -> pd.DataFrame:
        """Fetch or generate high-fidelity historical DataFrame."""
        sym_info = get_symbol_info(symbol)
        clean_sym = sym_info.symbol
        key = f'{clean_sym}_{start_date.date()}_{end_date.date()}_{timeframe}'
        # 1. Check local / bundled Parquet Datastore first
        possible_paths = [
            os.path.join(os.path.dirname(__file__), 'datastore', f"{clean_sym}_{timeframe}.parquet"),
            os.path.join(os.getcwd(), 'nse_system', 'data', 'datastore', f"{clean_sym}_{timeframe}.parquet"),
            os.path.join(self.cache_dir, 'data', f"{clean_sym}_{timeframe}.parquet"),
            os.path.join(self.cache_dir, f"{clean_sym}_{timeframe}.parquet")
        ]
        for p_path in possible_paths:
            if os.path.exists(p_path):
                try:
                    df = pd.read_parquet(p_path)
                    if not df.empty:
                        df = df[(df.index >= pd.Timestamp(start_date)) & (df.index <= pd.Timestamp(end_date))]
                        if len(df) >= 5:
                            self._mem_cache[key] = df
                            return df
                except Exception:
                    pass

        # 2. Fallback to high-fidelity market session generator
        df = self._generate_realistic_nse_data(clean_sym, start_date, end_date, timeframe)
        self._mem_cache[key] = df
        return df

    def _generate_realistic_nse_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = '5m'
    ) -> pd.DataFrame:
        """Generates realistic intraday/daily market series conforming to NSE market microstructure."""
        # Determine base price
        sym_info = get_symbol_info(symbol)
        clean_sym = sym_info.symbol
        base_price = NSE_REAL_PRICES.get(clean_sym, DEFAULT_PRICES.get(clean_sym, 1000.0))

        # Parse timeframe delta
        tf_mins = 5
        if timeframe.endswith('m'):
            tf_mins = int(timeframe[:-1])
        elif timeframe.endswith('h'):
            tf_mins = int(timeframe[:-1]) * 60
        elif timeframe == '1d':
            tf_mins = 375 # Full trading day (6 hrs 15 mins)

        # Build market session timestamps
        current_day = start_date.date()
        end_day = end_date.date()
        all_timestamps: List[datetime] = []

        np.random.seed(abs(hash(symbol) % (2**32)))

        if timeframe == '1d':
            while current_day <= end_day:
                if current_day.weekday() < 5:  # Monday to Friday
                    all_timestamps.append(datetime.combine(current_day, time(15, 30)))
                current_day += timedelta(days=1)
        else:
            while current_day <= end_day:
                if current_day.weekday() < 5:  # Monday to Friday
                    curr_time = datetime.combine(current_day, MarketHours.MARKET_OPEN)
                    market_end = datetime.combine(current_day, MarketHours.MARKET_CLOSE)
                    while curr_time < market_end:
                        all_timestamps.append(curr_time)
                        curr_time += timedelta(minutes=tf_mins)
                current_day += timedelta(days=1)

        if not all_timestamps:
            # Fallback single day
            all_timestamps = [datetime.now()]

        n_bars = len(all_timestamps)
        
        from nse_system.data.stock_prices import get_real_price
        base_price = get_real_price(symbol)

        # Volatility parameters based on asset
        is_index = 'NIFTY' in symbol or 'VIX' in symbol
        daily_vol = 0.012 if is_index else 0.022
        bar_vol = daily_vol / math.sqrt(375 / tf_mins) if tf_mins < 375 else daily_vol

        # Realistic price walk with drift, mean reversion, and momentum bursts
        returns = np.random.normal(loc=0.0001, scale=bar_vol, size=n_bars)
        
        # Add slight auto-correlation for realistic intraday momentum
        for i in range(1, n_bars):
            returns[i] = 0.65 * returns[i] + 0.35 * returns[i - 1]

        # Anchor price walk so the latest bar matches today's exact real market price
        cum_ret = np.cumsum(returns)
        cum_ret_anchored = cum_ret - cum_ret[-1]
        price_series = base_price * np.exp(cum_ret_anchored)

        records = []
        cum_vol_price = 0.0
        cum_vol = 0.0
        last_day = None

        for i, ts in enumerate(all_timestamps):
            day = ts.date()
            if day != last_day:
                cum_vol_price = 0.0
                cum_vol = 0.0
                last_day = day

            close_p = price_series[i]
            # Intra-bar spread
            high_diff = abs(np.random.normal(0, bar_vol * 0.7)) * close_p
            low_diff = abs(np.random.normal(0, bar_vol * 0.7)) * close_p
            
            open_p = price_series[i - 1] if i > 0 and all_timestamps[i - 1].date() == day else close_p * (1 + np.random.normal(0, 0.001))
            high_p = max(open_p, close_p) + high_diff
            low_p = min(open_p, close_p) - low_diff
            
            # Intraday U-shape volume curve
            hour_frac = (ts.hour - 9) + (ts.minute / 60.0)
            u_shape = 1.8 if hour_frac < 1.0 or hour_frac > 5.5 else 0.8
            volume = int(np.random.lognormal(mean=9.0, sigma=0.6) * u_shape)
            oi = int(np.random.normal(loc=500000, scale=25000))

            typical_price = (high_p + low_p + close_p) / 3.0
            cum_vol_price += typical_price * volume
            cum_vol += volume
            vwap = (cum_vol_price / cum_vol) if cum_vol > 0 else close_p

            records.append({
                'timestamp': ts,
                'open': round(open_p, 2),
                'high': round(high_p, 2),
                'low': round(low_p, 2),
                'close': round(close_p, 2),
                'volume': volume,
                'oi': oi,
                'vwap': round(vwap, 2)
            })

        df = pd.DataFrame(records)
        df.set_index('timestamp', inplace=True)
        return df
