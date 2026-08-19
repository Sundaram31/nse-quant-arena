"""Vectorized & Streaming Technical Indicators for Indian Equity & F&O Markets."""
from typing import Tuple, Optional
import numpy as np
import pandas as pd

def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()

def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=period).mean()

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index with Wilder's Smoothing."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    # Wilder's exponential smoothing (alpha = 1 / period)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_val = 100.0 - (100.0 / (1.0 + rs))
    return rsi_val.fillna(50.0)

def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range."""
    high = df['high']
    low = df['low']
    close = df['close'].shift(1)
    
    tr1 = high - low
    tr2 = (high - close).abs()
    tr3 = (low - close).abs()
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

def supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> pd.DataFrame:
    """Calculates SuperTrend indicator. Returns DataFrame with 'supertrend' and 'supertrend_direction'."""
    df_res = df.copy()
    atr_val = atr(df, period=period)
    hl2 = (df['high'] + df['low']) / 2.0
    
    basic_upper = hl2 + (multiplier * atr_val)
    basic_lower = hl2 - (multiplier * atr_val)
    
    final_upper = pd.Series(index=df.index, dtype=float)
    final_lower = pd.Series(index=df.index, dtype=float)
    st = pd.Series(index=df.index, dtype=float)
    direction = pd.Series(index=df.index, dtype=int)
    
    close = df['close'].values
    b_upper = basic_upper.values
    b_lower = basic_lower.values
    
    n = len(df)
    f_upper = np.zeros(n)
    f_lower = np.zeros(n)
    st_arr = np.zeros(n)
    dir_arr = np.ones(n, dtype=int)
    
    for i in range(1, n):
        # Upper band
        if b_upper[i] < f_upper[i-1] or close[i-1] > f_upper[i-1]:
            f_upper[i] = b_upper[i]
        else:
            f_upper[i] = f_upper[i-1]
            
        # Lower band
        if b_lower[i] > f_lower[i-1] or close[i-1] < f_lower[i-1]:
            f_lower[i] = b_lower[i]
        else:
            f_lower[i] = f_lower[i-1]
            
        # Direction & Supertrend
        if dir_arr[i-1] == 1:
            if close[i] < f_lower[i]:
                dir_arr[i] = -1
                st_arr[i] = f_upper[i]
            else:
                dir_arr[i] = 1
                st_arr[i] = f_lower[i]
        else:
            if close[i] > f_upper[i]:
                dir_arr[i] = 1
                st_arr[i] = f_lower[i]
            else:
                dir_arr[i] = -1
                st_arr[i] = f_upper[i]

    df_res['supertrend'] = st_arr
    df_res['supertrend_direction'] = dir_arr
    return df_res

def vwap(df: pd.DataFrame) -> pd.DataFrame:
    """Calculates session-aware VWAP with 1-SD and 2-SD standard deviation bands."""
    df_res = df.copy()
    
    typical_price = (df['high'] + df['low'] + df['close']) / 3.0
    vol = df['volume'].replace(0, 1.0)
    
    # Fast date extraction without pd.to_datetime overhead
    if isinstance(df.index, pd.DatetimeIndex):
        dates = df.index.date
    else:
        dates = [ts.date() if hasattr(ts, 'date') else ts for ts in df.index]
    
    vwap_vals = []
    sd1_upper = []
    sd1_lower = []
    sd2_upper = []
    sd2_lower = []
    
    cum_pv = 0.0
    cum_v = 0.0
    cum_pv_sq = 0.0
    last_date = None
    
    for tp, v, d in zip(typical_price.values, vol.values, dates):
        if d != last_date:
            cum_pv = 0.0
            cum_v = 0.0
            cum_pv_sq = 0.0
            last_date = d
            
        cum_pv += tp * v
        cum_v += v
        cum_pv_sq += (tp ** 2) * v
        
        cur_vwap = cum_pv / cum_v
        variance = max(0.0, (cum_pv_sq / cum_v) - (cur_vwap ** 2))
        std_dev = np.sqrt(variance)
        
        vwap_vals.append(cur_vwap)
        sd1_upper.append(cur_vwap + std_dev)
        sd1_lower.append(cur_vwap - std_dev)
        sd2_upper.append(cur_vwap + 2.0 * std_dev)
        sd2_lower.append(cur_vwap - 2.0 * std_dev)
        
    df_res['vwap'] = vwap_vals
    df_res['vwap_sd1_upper'] = sd1_upper
    df_res['vwap_sd1_lower'] = sd1_lower
    df_res['vwap_sd2_upper'] = sd2_upper
    df_res['vwap_sd2_lower'] = sd2_lower
    return df_res

def bollinger_bands(series: pd.Series, period: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    """Bollinger Bands: Middle (SMA), Upper, Lower, Bandwidth, %B."""
    mid = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = mid + (num_std * std)
    lower = mid - (num_std * std)
    bandwidth = (upper - lower) / mid.replace(0, np.nan)
    percent_b = (series - lower) / (upper - lower).replace(0, np.nan)
    
    return pd.DataFrame({
        'bb_middle': mid,
        'bb_upper': upper,
        'bb_lower': lower,
        'bb_bandwidth': bandwidth,
        'bb_percent_b': percent_b
    }, index=series.index)

def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """MACD line, Signal line, Histogram."""
    fast_ema = ema(series, fast)
    slow_ema = ema(series, slow)
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    
    return pd.DataFrame({
        'macd_line': macd_line,
        'macd_signal': signal_line,
        'macd_hist': histogram
    }, index=series.index)

def adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Average Directional Index (ADX) & Directional Movement (+DI, -DI)."""
    high = df['high']
    low = df['low']
    
    up_move = high.diff()
    down_move = -low.diff()
    
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    
    atr_val = atr(df, period=period)
    
    plus_di = 100.0 * pd.Series(plus_dm, index=df.index).ewm(alpha=1.0/period, adjust=False).mean() / atr_val.replace(0, np.nan)
    minus_di = 100.0 * pd.Series(minus_dm, index=df.index).ewm(alpha=1.0/period, adjust=False).mean() / atr_val.replace(0, np.nan)
    
    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx_val = dx.ewm(alpha=1.0/period, adjust=False).mean()
    
    return pd.DataFrame({
        'plus_di': plus_di.fillna(0.0),
        'minus_di': minus_di.fillna(0.0),
        'adx': adx_val.fillna(20.0)
    }, index=df.index)
