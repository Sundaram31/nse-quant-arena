"""Helega Milega (HM) Indian Momentum & RSI Smoothed Indicator Strategy (Incremental)."""
from typing import Optional, List, Dict, Any
from collections import deque

from nse_system.core.models import Candle, Signal
from nse_system.core.constants import SignalType, ProductType
from nse_system.strategies.base import BaseStrategy

class HelegaMilegaStrategy(BaseStrategy):
    """
    Helega Milega (HM) Strategy:
    Combines Smoothed RSI (9 EMA of RSI vs 21 EMA of RSI) with VWAP and Volume surge.
    Popularized in Indian markets for high-conviction directional momentum.
    """

    def __init__(self, symbol: str, timeframe: str = '5m', params: Optional[Dict[str, Any]] = None):
        default_params = {
            'rsi_period': 14,
            'fast_ema': 9,
            'slow_ema': 21,
            'vol_multiplier': 1.1,
            'atr_sl_mult': 1.5,
            'risk_reward': 2.0
        }
        if params:
            default_params.update(params)
        super().__init__(name='Helega_Milega', symbol=symbol, timeframe=timeframe, params=default_params)
        self._reset()

    def _reset(self):
        self.avg_gain: float = 0.0
        self.avg_loss: float = 0.0
        self.rsi_val: float = 50.0
        self.fast_line: float = 50.0
        self.slow_line: float = 50.0
        self.prev_fast: float = 50.0
        self.prev_slow: float = 50.0
        self.atr_val: float = 0.0
        self.vol_window: deque = deque(maxlen=20)

    def on_start(self):
        super().on_start()
        self._reset()

    def on_candle(self, candle: Candle, historical_candles: Optional[List[Candle]] = None) -> Optional[Signal]:
        self.candles.append(candle)
        cur_close = candle.close
        cur_vol = candle.volume
        self.vol_window.append(cur_vol)

        if len(self.candles) == 1:
            self.atr_val = candle.high - candle.low
            return None

        prev_close = self.candles[-2].close
        diff = cur_close - prev_close
        gain = max(0.0, diff)
        loss = max(0.0, -diff)

        a_rsi = 1.0 / self.params['rsi_period']
        self.avg_gain = a_rsi * gain + (1 - a_rsi) * self.avg_gain
        self.avg_loss = a_rsi * loss + (1 - a_rsi) * self.avg_loss
        rs = self.avg_gain / max(1e-6, self.avg_loss)
        self.rsi_val = 100.0 - (100.0 / (1.0 + rs))

        self.prev_fast = self.fast_line
        self.prev_slow = self.slow_line

        a_fast = 2.0 / (self.params['fast_ema'] + 1.0)
        a_slow = 2.0 / (self.params['slow_ema'] + 1.0)
        self.fast_line = a_fast * self.rsi_val + (1 - a_fast) * self.fast_line
        self.slow_line = a_slow * self.rsi_val + (1 - a_slow) * self.slow_line

        tr = max(candle.high - candle.low, abs(candle.high - prev_close), abs(candle.low - prev_close))
        self.atr_val = a_rsi * tr + (1 - a_rsi) * self.atr_val

        if len(self.candles) < self.params['slow_ema']:
            return None

        vol_avg = sum(self.vol_window) / len(self.vol_window)
        has_volume = bool(cur_vol >= (vol_avg * self.params['vol_multiplier']))
        rel_vol = float(cur_vol / max(1.0, vol_avg))

        # Check Position Exits
        if self.current_position > 0:
            if self.stop_loss and candle.low <= self.stop_loss:
                return self.exit_signal(candle, reason='Helega Milega Stop Loss Hit')
            if self.target and candle.high >= self.target:
                return self.exit_signal(candle, reason='Helega Milega Target Hit')
            if self.fast_line < self.slow_line and self.prev_fast >= self.prev_slow:
                return self.exit_signal(candle, reason='Fast Line crossed below Slow Line')

        elif self.current_position < 0:
            if self.stop_loss and candle.high >= self.stop_loss:
                return self.exit_signal(candle, reason='Helega Milega Short Stop Loss Hit')
            if self.target and candle.low <= self.target:
                return self.exit_signal(candle, reason='Helega Milega Short Target Hit')
            if self.fast_line > self.slow_line and self.prev_fast <= self.prev_slow:
                return self.exit_signal(candle, reason='Fast Line crossed above Slow Line')

        # Long Signal: Fast crosses above Slow, Fast > 45, Volume surge
        if self.current_position == 0 and self.prev_fast <= self.prev_slow and self.fast_line > self.slow_line and self.fast_line >= 45.0 and has_volume:
            sl = cur_close - (self.atr_val * self.params['atr_sl_mult'])
            risk = max(1.0, cur_close - sl)
            target = cur_close + (risk * self.params['risk_reward'])
            self.stop_loss = sl
            self.target = target
            return Signal(
                timestamp=candle.timestamp,
                symbol=self.symbol,
                signal_type=SignalType.BUY.value,
                price=cur_close,
                stop_loss=round(sl, 2),
                target=round(target, 2),
                confidence=0.88,
                reason=f'Helega Milega Bullish (Fast: {self.fast_line:.1f} > Slow: {self.slow_line:.1f}, Vol: {rel_vol:.1f}x)'
            )

        # Short Signal: Fast crosses below Slow, Fast < 55, Volume surge
        if self.current_position == 0 and self.prev_fast >= self.prev_slow and self.fast_line < self.slow_line and self.fast_line <= 55.0 and has_volume:
            sl = cur_close + (self.atr_val * self.params['atr_sl_mult'])
            risk = max(1.0, sl - cur_close)
            target = cur_close - (risk * self.params['risk_reward'])
            self.stop_loss = sl
            self.target = target
            return Signal(
                timestamp=candle.timestamp,
                symbol=self.symbol,
                signal_type=SignalType.SELL.value,
                price=cur_close,
                stop_loss=round(sl, 2),
                target=round(target, 2),
                confidence=0.88,
                reason=f'Helega Milega Bearish (Fast: {self.fast_line:.1f} < Slow: {self.slow_line:.1f}, Vol: {rel_vol:.1f}x)'
            )

        return None
