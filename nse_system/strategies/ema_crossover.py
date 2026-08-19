"""Multi-Timeframe EMA Crossover (9/21/200 EMA + RSI Filter) Strategy (Incremental)."""
from datetime import time
from typing import Optional, Dict, Any
from nse_system.core.models import Candle, Signal
from nse_system.strategies.base import BaseStrategy

class MultiEMACrossoverStrategy(BaseStrategy):
    """Enters on 9 EMA crossing 21 EMA in the direction of the 200 EMA trend with RSI confirmation."""

    def __init__(self, symbol: str, timeframe: str = '5m', params: Optional[Dict[str, Any]] = None):
        default_params = {
            'fast_ema': 9,
            'slow_ema': 21,
            'trend_ema': 200,
            'rsi_period': 14,
            'rsi_bull_min': 52.0,
            'rsi_bear_max': 48.0,
            'risk_reward': 2.0,
            'atr_sl_mult': 1.5
        }
        if params:
            default_params.update(params)
        super().__init__('Multi-EMA Crossover + RSI', symbol, timeframe, default_params)
        self._reset()

    def _reset(self):
        self.fast_ema_val: float = 0.0
        self.slow_ema_val: float = 0.0
        self.trend_ema_val: float = 0.0
        self.avg_gain: float = 0.0
        self.avg_loss: float = 0.0
        self.rsi_val: float = 50.0
        self.atr_val: float = 0.0
        self.prev_fast: float = 0.0
        self.prev_slow: float = 0.0

    def on_start(self):
        super().on_start()
        self._reset()

    def on_candle(self, candle: Candle) -> Optional[Signal]:
        self.candles.append(candle)
        c_time = candle.timestamp.time()
        cur_close = candle.close

        # Incremental EMAs
        if len(self.candles) == 1:
            self.fast_ema_val = cur_close
            self.slow_ema_val = cur_close
            self.trend_ema_val = cur_close
            self.atr_val = candle.high - candle.low
            return None

        self.prev_fast = self.fast_ema_val
        self.prev_slow = self.slow_ema_val

        a_fast = 2.0 / (self.params['fast_ema'] + 1.0)
        a_slow = 2.0 / (self.params['slow_ema'] + 1.0)
        a_trend = 2.0 / (min(len(self.candles), self.params['trend_ema']) + 1.0)

        self.fast_ema_val = a_fast * cur_close + (1 - a_fast) * self.fast_ema_val
        self.slow_ema_val = a_slow * cur_close + (1 - a_slow) * self.slow_ema_val
        self.trend_ema_val = a_trend * cur_close + (1 - a_trend) * self.trend_ema_val

        # Incremental RSI & ATR
        prev_close = self.candles[-2].close
        diff = cur_close - prev_close
        gain = max(0.0, diff)
        loss = max(0.0, -diff)
        a_rsi = 1.0 / self.params['rsi_period']
        self.avg_gain = a_rsi * gain + (1 - a_rsi) * self.avg_gain
        self.avg_loss = a_rsi * loss + (1 - a_rsi) * self.avg_loss
        rs = self.avg_gain / max(1e-6, self.avg_loss)
        self.rsi_val = 100.0 - (100.0 / (1.0 + rs))

        tr = max(candle.high - candle.low, abs(candle.high - prev_close), abs(candle.low - prev_close))
        self.atr_val = a_rsi * tr + (1 - a_rsi) * self.atr_val

        if len(self.candles) < self.params['slow_ema']:
            return None

        if c_time >= time(15, 15):
            if self.current_position != 0:
                return self.exit_signal(candle, reason='15:15 Intraday Square-Off')
            return None

        f_cur = self.fast_ema_val
        s_cur = self.slow_ema_val
        f_prev = self.prev_fast
        s_prev = self.prev_slow
        t_cur = self.trend_ema_val
        r_cur = self.rsi_val

        # Position Exits
        if self.current_position > 0:
            if self.stop_loss and candle.low <= self.stop_loss:
                return self.exit_signal(candle, reason='Long EMA Stop Loss Hit')
            if self.target and candle.high >= self.target:
                return self.exit_signal(candle, reason='Long EMA Target Hit')
            if f_cur < s_cur and f_prev >= s_prev:
                return self.exit_signal(candle, reason='Fast EMA Crossed Below Slow EMA')

        elif self.current_position < 0:
            if self.stop_loss and candle.high >= self.stop_loss:
                return self.exit_signal(candle, reason='Short EMA Stop Loss Hit')
            if self.target and candle.low <= self.target:
                return self.exit_signal(candle, reason='Short EMA Target Hit')
            if f_cur > s_cur and f_prev <= s_prev:
                return self.exit_signal(candle, reason='Fast EMA Crossed Above Slow EMA')

        # Entry logic
        if self.current_position == 0 and time(9, 30) <= c_time <= time(14, 30):
            if f_cur > s_cur and f_prev <= s_prev and cur_close > t_cur and r_cur >= self.params['rsi_bull_min']:
                sl = cur_close - (self.params['atr_sl_mult'] * self.atr_val)
                risk = cur_close - sl
                tgt = cur_close + (risk * self.params['risk_reward'])
                self.stop_loss = sl
                self.target = tgt
                return self.buy_signal(
                    candle, stop_loss=round(sl, 2), target=round(tgt, 2),
                    reason=f'Golden Cross (9/21 EMA) | Trend > 200 EMA | RSI={r_cur:.1f}',
                    confidence=0.86
                )
            elif f_cur < s_cur and f_prev >= s_prev and cur_close < t_cur and r_cur <= self.params['rsi_bear_max']:
                sl = cur_close + (self.params['atr_sl_mult'] * self.atr_val)
                risk = sl - cur_close
                tgt = cur_close - (risk * self.params['risk_reward'])
                self.stop_loss = sl
                self.target = tgt
                return self.sell_signal(
                    candle, stop_loss=round(sl, 2), target=round(tgt, 2),
                    reason=f'Death Cross (9/21 EMA) | Trend < 200 EMA | RSI={r_cur:.1f}',
                    confidence=0.86
                )

        return None
