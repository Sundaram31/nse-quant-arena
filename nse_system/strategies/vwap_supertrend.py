"""VWAP + SuperTrend Multi-Indicator Trend-Following Strategy (High Performance Incremental Engine)."""
from datetime import time
from typing import Optional, Dict, Any
from nse_system.core.models import Candle, Signal
from nse_system.strategies.base import BaseStrategy

class VWAPSuperTrendStrategy(BaseStrategy):
    """Trend following system: Enters when price aligns with VWAP and Supertrend confirms direction."""

    def __init__(self, symbol: str, timeframe: str = '5m', params: Optional[Dict[str, Any]] = None):
        default_params = {
            'st_period': 10,
            'st_multiplier': 3.0,
            'atr_multiplier_sl': 1.5,
            'risk_reward': 2.0,
            'trailing_sl': True
        }
        if params:
            default_params.update(params)
        super().__init__('VWAP + SuperTrend Trend Rider', symbol, timeframe, default_params)
        self.highest_price: float = 0.0
        self.lowest_price: float = float('inf')
        self._reset_indicators()

    def _reset_indicators(self):
        self.atr_val: float = 0.0
        self.f_upper: float = float('inf')
        self.f_lower: float = 0.0
        self.st_dir: int = 1
        self.supertrend: float = 0.0
        self.cum_pv: float = 0.0
        self.cum_v: float = 0.0
        self.current_date = None

    def on_start(self):
        super().on_start()
        self._reset_indicators()

    def on_candle(self, candle: Candle) -> Optional[Signal]:
        self.candles.append(candle)
        c_time = candle.timestamp.time()
        c_date = candle.timestamp.date()

        # Daily VWAP accumulator reset
        if c_date != self.current_date:
            self.cum_pv = 0.0
            self.cum_v = 0.0
            self.current_date = c_date

        typical_price = (candle.high + candle.low + candle.close) / 3.0
        vol = candle.volume if candle.volume > 0 else 1.0
        self.cum_pv += typical_price * vol
        self.cum_v += vol
        cur_vwap = candle.vwap if candle.vwap else (self.cum_pv / self.cum_v)

        # Incremental ATR & Supertrend
        if len(self.candles) == 1:
            self.atr_val = candle.high - candle.low
            self.f_upper = candle.high
            self.f_lower = candle.low
            return None

        prev_c = self.candles[-2].close
        tr = max(candle.high - candle.low, abs(candle.high - prev_c), abs(candle.low - prev_c))
        alpha = 1.0 / self.params['st_period']
        self.atr_val = alpha * tr + (1.0 - alpha) * self.atr_val

        hl2 = (candle.high + candle.low) / 2.0
        b_upper = hl2 + (self.params['st_multiplier'] * self.atr_val)
        b_lower = hl2 - (self.params['st_multiplier'] * self.atr_val)

        if b_upper < self.f_upper or prev_c > self.f_upper:
            self.f_upper = b_upper
        if b_lower > self.f_lower or prev_c < self.f_lower:
            self.f_lower = b_lower

        if self.st_dir == 1:
            if candle.close < self.f_lower:
                self.st_dir = -1
                self.supertrend = self.f_upper
            else:
                self.st_dir = 1
                self.supertrend = self.f_lower
        else:
            if candle.close > self.f_upper:
                self.st_dir = 1
                self.supertrend = self.f_lower
            else:
                self.st_dir = -1
                self.supertrend = self.f_upper

        if len(self.candles) < self.params['st_period']:
            return None

        # Mandatory 15:15 IST Square-off
        if c_time >= time(15, 15):
            if self.current_position != 0:
                return self.exit_signal(candle, reason='Intraday 15:15 Square-Off')
            return None

        cur_close = candle.close
        cur_atr = self.atr_val

        # Check Position Exits & Trailing Stop Loss
        if self.current_position > 0:
            self.highest_price = max(self.highest_price, candle.high)
            if self.params['trailing_sl']:
                trail_sl = self.highest_price - (self.params['atr_multiplier_sl'] * cur_atr)
                if self.stop_loss is None or trail_sl > self.stop_loss:
                    self.stop_loss = trail_sl

            if self.stop_loss and candle.low <= self.stop_loss:
                return self.exit_signal(candle, reason='Long Trailing SL Hit')
            if self.target and candle.high >= self.target:
                return self.exit_signal(candle, reason='Long Target Hit')
            if self.st_dir == -1:
                return self.exit_signal(candle, reason='SuperTrend flipped Bearish')

        elif self.current_position < 0:
            self.lowest_price = min(self.lowest_price, candle.low)
            if self.params['trailing_sl']:
                trail_sl = self.lowest_price + (self.params['atr_multiplier_sl'] * cur_atr)
                if self.stop_loss is None or trail_sl < self.stop_loss:
                    self.stop_loss = trail_sl

            if self.stop_loss and candle.high >= self.stop_loss:
                return self.exit_signal(candle, reason='Short Trailing SL Hit')
            if self.target and candle.low <= self.target:
                return self.exit_signal(candle, reason='Short Target Hit')
            if self.st_dir == 1:
                return self.exit_signal(candle, reason='SuperTrend flipped Bullish')

        # Check Entry Conditions
        if self.current_position == 0 and time(9, 30) <= c_time <= time(14, 30):
            if cur_close > cur_vwap and self.st_dir == 1:
                sl = cur_close - (self.params['atr_multiplier_sl'] * cur_atr)
                risk = cur_close - sl
                tgt = cur_close + (risk * self.params['risk_reward'])
                self.stop_loss = sl
                self.target = tgt
                self.highest_price = cur_close
                return self.buy_signal(
                    candle,
                    stop_loss=round(sl, 2),
                    target=round(tgt, 2),
                    reason=f'Bullish: Price ({cur_close:.2f}) > VWAP ({cur_vwap:.2f}) & Supertrend Green',
                    confidence=0.88
                )

            elif cur_close < cur_vwap and self.st_dir == -1:
                sl = cur_close + (self.params['atr_multiplier_sl'] * cur_atr)
                risk = sl - cur_close
                tgt = cur_close - (risk * self.params['risk_reward'])
                self.stop_loss = sl
                self.target = tgt
                self.lowest_price = cur_close
                return self.sell_signal(
                    candle,
                    stop_loss=round(sl, 2),
                    target=round(tgt, 2),
                    reason=f'Bearish: Price ({cur_close:.2f}) < VWAP ({cur_vwap:.2f}) & Supertrend Red',
                    confidence=0.88
                )

        return None
