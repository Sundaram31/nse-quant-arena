"""Price Volume Action (PVA) Breakout Strategy with Volume Footprint (Incremental)."""
from typing import Optional, List, Dict, Any
from collections import deque

from nse_system.core.models import Candle, Signal
from nse_system.core.constants import SignalType, ProductType
from nse_system.strategies.base import BaseStrategy

class PriceVolumeActionStrategy(BaseStrategy):
    """
    Price-Volume Action (PVA) Breakout Strategy:
    Enters on institutional volume surges accompanying price expansion above/below N-bar consolidation pivots.
    """

    def __init__(self, symbol: str, timeframe: str = '5m', params: Optional[Dict[str, Any]] = None):
        default_params = {
            'lookback_pivot': 20,
            'vol_threshold': 1.2,
            'body_threshold': 0.45,
            'risk_reward': 2.0
        }
        if params:
            default_params.update(params)
        super().__init__(name='Price_Volume_Action', symbol=symbol, timeframe=timeframe, params=default_params)
        self._reset()

    def _reset(self):
        self.high_window: deque = deque(maxlen=self.params['lookback_pivot'])
        self.low_window: deque = deque(maxlen=self.params['lookback_pivot'])
        self.vol_window: deque = deque(maxlen=20)
        self.atr_val: float = 0.0

    def on_start(self):
        super().on_start()
        self._reset()

    def on_candle(self, candle: Candle, historical_candles: Optional[List[Candle]] = None) -> Optional[Signal]:
        self.candles.append(candle)
        cur_open = candle.open
        cur_high = candle.high
        cur_low = candle.low
        cur_close = candle.close
        cur_vol = candle.volume

        if len(self.candles) == 1:
            self.atr_val = cur_high - cur_low
            self.high_window.append(cur_high)
            self.low_window.append(cur_low)
            self.vol_window.append(cur_vol)
            return None

        prev_close = self.candles[-2].close
        a_atr = 1.0 / 14.0
        tr = max(cur_high - cur_low, abs(cur_high - prev_close), abs(cur_low - prev_close))
        self.atr_val = a_atr * tr + (1 - a_atr) * self.atr_val

        # Check Position Exits
        if self.current_position > 0:
            if self.stop_loss and cur_low <= self.stop_loss:
                return self.exit_signal(candle, reason='PVA Stop Loss Hit')
            if self.target and cur_high >= self.target:
                return self.exit_signal(candle, reason='PVA Target Hit')

        elif self.current_position < 0:
            if self.stop_loss and cur_high >= self.stop_loss:
                return self.exit_signal(candle, reason='PVA Short Stop Loss Hit')
            if self.target and cur_low <= self.target:
                return self.exit_signal(candle, reason='PVA Short Target Hit')

        # Need full lookback window to evaluate pivots
        if len(self.high_window) < self.params['lookback_pivot']:
            self.high_window.append(cur_high)
            self.low_window.append(cur_low)
            self.vol_window.append(cur_vol)
            return None

        pivot_high = max(self.high_window)
        pivot_low = min(self.low_window)
        vol_avg = sum(self.vol_window) / len(self.vol_window)
        rel_vol = float(cur_vol / max(1.0, vol_avg))

        candle_range = max(0.1, cur_high - cur_low)
        body_size = abs(cur_close - cur_open)
        body_pct = float(body_size / candle_range)

        # Bullish PVA Breakout
        if self.current_position == 0 and cur_close > cur_open and cur_close > pivot_high and rel_vol >= self.params['vol_threshold'] and body_pct >= self.params['body_threshold']:
            sl = cur_low - (self.atr_val * 0.5)
            risk = max(1.0, cur_close - sl)
            target = cur_close + (risk * self.params['risk_reward'])
            self.stop_loss = sl
            self.target = target
            self.high_window.append(cur_high)
            self.low_window.append(cur_low)
            self.vol_window.append(cur_vol)
            return Signal(
                timestamp=candle.timestamp,
                symbol=self.symbol,
                signal_type=SignalType.BUY.value,
                price=cur_close,
                stop_loss=round(sl, 2),
                target=round(target, 2),
                confidence=0.90,
                reason=f'Institutional PVA Bullish (RelVol: {rel_vol:.1f}x, Body: {body_pct*100:.0f}%)'
            )

        # Bearish PVA Breakdown
        if self.current_position == 0 and cur_close < cur_open and cur_close < pivot_low and rel_vol >= self.params['vol_threshold'] and body_pct >= self.params['body_threshold']:
            sl = cur_high + (self.atr_val * 0.5)
            risk = max(1.0, sl - cur_close)
            target = cur_close - (risk * self.params['risk_reward'])
            self.stop_loss = sl
            self.target = target
            self.high_window.append(cur_high)
            self.low_window.append(cur_low)
            self.vol_window.append(cur_vol)
            return Signal(
                timestamp=candle.timestamp,
                symbol=self.symbol,
                signal_type=SignalType.SELL.value,
                price=cur_close,
                stop_loss=round(sl, 2),
                target=round(target, 2),
                confidence=0.90,
                reason=f'Institutional PVA Bearish (RelVol: {rel_vol:.1f}x, Body: {body_pct*100:.0f}%)'
            )

        self.high_window.append(cur_high)
        self.low_window.append(cur_low)
        self.vol_window.append(cur_vol)
        return None
