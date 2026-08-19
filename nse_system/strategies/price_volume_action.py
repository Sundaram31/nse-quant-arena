"""Price-Volume Action (PVA) & Institutional Footprint Breakout Strategy."""
from typing import Optional, List
import pandas as pd
import numpy as np

from nse_system.core.models import Candle, Signal
from nse_system.core.constants import SignalType, ProductType
from nse_system.strategies.base import BaseStrategy
from nse_system.indicators.technical import atr, vwap

class PriceVolumeActionStrategy(BaseStrategy):
    """
    Price-Volume Action (PVA) Strategy:
    Detects institutional accumulation/distribution footprints by analyzing:
    1. Ultra-High Relative Volume (> 1.8x 20-bar average).
    2. Strong Candle Body (> 55% of candle range, indicating conviction).
    3. Multi-bar Resistance/Support breakout.
    """

    def __init__(self, symbol: str, timeframe: str = '5m', params: dict = None):
        default_params = {
            'lookback_pivot': 20,
            'vol_threshold': 1.6,
            'body_threshold': 0.55,
            'atr_sl_mult': 1.5,
            'risk_reward': 2.0
        }
        if params:
            default_params.update(params)
        super().__init__(name='Price_Volume_Action', symbol=symbol, timeframe=timeframe, params=default_params)

    def on_candle(self, candle: Candle, historical_candles: Optional[List[Candle]] = None) -> Optional[Signal]:
        self.candles.append(candle)
        candles_to_use = historical_candles or self.candles
        lookback = self.params['lookback_pivot']
        if len(candles_to_use) < lookback + 5:
            return None

        df = pd.DataFrame([{
            'open': c.open, 'high': c.high, 'low': c.low, 'close': c.close, 'volume': c.volume
        } for c in candles_to_use], index=[c.timestamp for c in candles_to_use])

        highs = df['high']
        lows = df['low']
        closes = df['close']
        opens = df['open']
        volumes = df['volume']

        curr_close = float(closes.iloc[-1])
        curr_open = float(opens.iloc[-1])
        curr_high = float(highs.iloc[-1])
        curr_low = float(lows.iloc[-1])
        curr_vol = float(volumes.iloc[-1])
        
        # Recent 20-bar High and Low (excluding current candle)
        pivot_high = float(highs.iloc[-lookback-1:-1].max())
        pivot_low = float(lows.iloc[-lookback-1:-1].min())

        vol_avg = float(volumes.iloc[-20:].mean()) if len(volumes) >= 20 else float(volumes.mean())
        rel_vol = float(curr_vol / max(1.0, vol_avg))

        candle_range = max(0.1, curr_high - curr_low)
        body_size = abs(curr_close - curr_open)
        body_pct = float(body_size / candle_range)

        atr_series = atr(df, 14)
        curr_atr = float(atr_series.iloc[-1])

        # Bullish PVA Breakout
        is_bullish_candle = curr_close > curr_open
        if is_bullish_candle and curr_close > pivot_high and rel_vol >= self.params['vol_threshold'] and body_pct >= self.params['body_threshold']:
            sl = curr_low - (curr_atr * 0.5)
            risk = max(1.0, curr_close - sl)
            target = curr_close + (risk * self.params['risk_reward'])
            return Signal(
                timestamp=candle.timestamp,
                symbol=self.symbol,
                signal_type=SignalType.BUY.value,
                price=curr_close,
                stop_loss=round(sl, 2),
                target=round(target, 2),
                confidence=0.90,
                reason=f'Institutional PVA Bullish Breakout (RelVol: {rel_vol:.1f}x, Body: {body_pct*100:.0f}%)'
            )

        # Bearish PVA Breakdown
        is_bearish_candle = curr_close < curr_open
        if is_bearish_candle and curr_close < pivot_low and rel_vol >= self.params['vol_threshold'] and body_pct >= self.params['body_threshold']:
            sl = curr_high + (curr_atr * 0.5)
            risk = max(1.0, sl - curr_close)
            target = curr_close - (risk * self.params['risk_reward'])
            return Signal(
                timestamp=candle.timestamp,
                symbol=self.symbol,
                signal_type=SignalType.SELL.value,
                price=curr_close,
                stop_loss=round(sl, 2),
                target=round(target, 2),
                confidence=0.90,
                reason=f'Institutional PVA Bearish Breakdown (RelVol: {rel_vol:.1f}x, Body: {body_pct*100:.0f}%)'
            )

        return None
