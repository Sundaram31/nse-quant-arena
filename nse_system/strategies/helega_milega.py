"""Helega Milega (HM) Indian Momentum & RSI Smoothed Indicator Strategy."""
from typing import Optional, List
import pandas as pd
import numpy as np

from nse_system.core.models import Candle, Signal
from nse_system.core.constants import SignalType, ProductType
from nse_system.strategies.base import BaseStrategy
from nse_system.indicators.technical import rsi, ema, vwap, atr

class HelegaMilegaStrategy(BaseStrategy):
    """
    Helega Milega (HM) Strategy:
    Combines Smoothed RSI (9 EMA of RSI vs 21 EMA of RSI) with VWAP and Volume surge.
    Popularized in Indian markets for high-conviction directional momentum.
    """

    def __init__(self, symbol: str, timeframe: str = '5m', params: dict = None):
        default_params = {
            'rsi_period': 14,
            'fast_ema': 9,
            'slow_ema': 21,
            'vol_multiplier': 1.2,
            'atr_sl_mult': 1.5,
            'risk_reward': 2.0
        }
        if params:
            default_params.update(params)
        super().__init__(name='Helega_Milega', symbol=symbol, timeframe=timeframe, params=default_params)

    def on_candle(self, candle: Candle, historical_candles: Optional[List[Candle]] = None) -> Optional[Signal]:
        self.candles.append(candle)
        candles_to_use = historical_candles or self.candles
        if len(candles_to_use) < 35:
            return None

        # Build DataFrame
        df = pd.DataFrame([{
            'open': c.open, 'high': c.high, 'low': c.low, 'close': c.close, 'volume': c.volume
        } for c in candles_to_use], index=[c.timestamp for c in candles_to_use])

        closes = df['close']
        volumes = df['volume']

        # 1. Calculate RSI and Smoothed RSI Lines
        rsi_series = rsi(closes, self.params['rsi_period'])
        fast_line = ema(rsi_series, self.params['fast_ema'])
        slow_line = ema(rsi_series, self.params['slow_ema'])
        
        # 2. VWAP & ATR
        vwap_df = vwap(df)
        atr_series = atr(df, 14)

        curr_fast = float(fast_line.iloc[-1])
        prev_fast = float(fast_line.iloc[-2])
        curr_slow = float(slow_line.iloc[-1])
        prev_slow = float(slow_line.iloc[-2])

        curr_close = float(closes.iloc[-1])
        curr_vwap = float(vwap_df['vwap'].iloc[-1])
        curr_atr = float(atr_series.iloc[-1])
        vol_avg = float(volumes.iloc[-20:].mean()) if len(volumes) >= 20 else float(volumes.mean())
        curr_vol = float(volumes.iloc[-1])
        has_volume = bool(curr_vol >= (vol_avg * self.params['vol_multiplier']))

        # Long Signal: Fast crosses above Slow, Fast > 50, Price > VWAP, Volume surge
        if prev_fast <= prev_slow and curr_fast > curr_slow and curr_fast >= 50.0 and curr_close > curr_vwap and has_volume:
            sl = curr_close - (curr_atr * self.params['atr_sl_mult'])
            risk = max(1.0, curr_close - sl)
            target = curr_close + (risk * self.params['risk_reward'])
            return Signal(
                timestamp=candle.timestamp,
                symbol=self.symbol,
                signal_type=SignalType.BUY.value,
                price=curr_close,
                stop_loss=round(sl, 2),
                target=round(target, 2),
                confidence=0.88,
                reason=f'Helega Milega Bullish Crossover (Fast: {curr_fast:.1f} > Slow: {curr_slow:.1f}, Vol: {curr_vol/vol_avg:.1f}x)'
            )

        # Short Signal: Fast crosses below Slow, Fast < 50, Price < VWAP, Volume surge
        if prev_fast >= prev_slow and curr_fast < curr_slow and curr_fast <= 50.0 and curr_close < curr_vwap and has_volume:
            sl = curr_close + (curr_atr * self.params['atr_sl_mult'])
            risk = max(1.0, sl - curr_close)
            target = curr_close - (risk * self.params['risk_reward'])
            return Signal(
                timestamp=candle.timestamp,
                symbol=self.symbol,
                signal_type=SignalType.SELL.value,
                price=curr_close,
                stop_loss=round(sl, 2),
                target=round(target, 2),
                confidence=0.88,
                reason=f'Helega Milega Bearish Breakdown (Fast: {curr_fast:.1f} < Slow: {curr_slow:.1f}, Vol: {curr_vol/vol_avg:.1f}x)'
            )

        return None
