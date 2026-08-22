"""Mean Reversion Bollinger Bands + RSI Oversold/Overbought Strategy (Optimized)."""
from datetime import time
from typing import Optional, Dict, Any
import numpy as np
from nse_system.core.models import Candle, Signal
from nse_system.strategies.base import BaseStrategy

class BollingerRSIStrategy(BaseStrategy):
    """Buys oversold bounces at lower band and shorts overbought rejections at upper band."""

    def __init__(self, symbol: str, timeframe: str = '5m', params: Optional[Dict[str, Any]] = None):
        default_params = {
            'bb_period': 20,
            'bb_std': 2.0,
            'rsi_period': 14,
            'rsi_oversold': 30.0,
            'rsi_overbought': 70.0,
            'risk_reward': 1.8
        }
        if params:
            default_params.update(params)
        super().__init__('Bollinger Bands + RSI Mean Reversion', symbol, timeframe, default_params)
        self.closes = []
        self.avg_gain = 0.0
        self.avg_loss = 0.0
        self.rsi_val = 50.0

    def on_start(self):
        super().on_start()
        self.closes = []
        self.avg_gain = 0.0
        self.avg_loss = 0.0
        self.rsi_val = 50.0

    def on_candle(self, candle: Candle) -> Optional[Signal]:
        self.candles.append(candle)
        self.closes.append(candle.close)
        c_time = candle.timestamp.time()
        cur_close = candle.close

        # Incremental RSI
        if len(self.closes) > 1:
            diff = cur_close - self.closes[-2]
            gain = max(0.0, diff)
            loss = max(0.0, -diff)
            a = 1.0 / self.params['rsi_period']
            self.avg_gain = a * gain + (1 - a) * self.avg_gain
            self.avg_loss = a * loss + (1 - a) * self.avg_loss
            rs = self.avg_gain / max(1e-6, self.avg_loss)
            self.rsi_val = 100.0 - (100.0 / (1.0 + rs))

        if len(self.closes) < self.params['bb_period']:
            return None

        # Bollinger Bands on last 20 closes
        window = self.closes[-self.params['bb_period']:]
        mid_band = sum(window) / len(window)
        std_val = float(np.std(window))
        upper_band = mid_band + (self.params['bb_std'] * std_val)
        lower_band = mid_band - (self.params['bb_std'] * std_val)
        pct_b = (cur_close - lower_band) / max(1e-6, upper_band - lower_band)

        is_daily = 'd' in str(self.timeframe).lower()

        if not is_daily and c_time >= time(15, 15):
            if self.current_position != 0:
                return self.exit_signal(candle, reason='15:15 Intraday Square-Off')
            return None

        # Position Exits
        if self.current_position > 0:
            if self.stop_loss and candle.low <= self.stop_loss:
                return self.exit_signal(candle, reason='Long Stop Loss Hit')
            if candle.high >= mid_band:
                return self.exit_signal(candle, reason='Mean Reversion Target (20 SMA) Reached')

        elif self.current_position < 0:
            if self.stop_loss and candle.high >= self.stop_loss:
                return self.exit_signal(candle, reason='Short Stop Loss Hit')
            if candle.low <= mid_band:
                return self.exit_signal(candle, reason='Mean Reversion Target (20 SMA) Reached')

        # Entry logic
        if self.current_position == 0 and (is_daily or (time(9, 30) <= c_time <= time(14, 15))):
            if (pct_b < 0.05 or candle.low <= lower_band) and self.rsi_val <= self.params['rsi_oversold']:
                sl = candle.low * 0.994
                tgt = mid_band
                self.stop_loss = sl
                self.target = tgt
                return self.buy_signal(
                    candle, stop_loss=round(sl, 2), target=round(tgt, 2),
                    reason=f'Oversold Bounce: %B={pct_b:.2f} | RSI={self.rsi_val:.1f}',
                    confidence=0.83
                )
            elif (pct_b > 0.95 or candle.high >= upper_band) and self.rsi_val >= self.params['rsi_overbought']:
                sl = candle.high * 1.006
                tgt = mid_band
                self.stop_loss = sl
                self.target = tgt
                return self.sell_signal(
                    candle, stop_loss=round(sl, 2), target=round(tgt, 2),
                    reason=f'Overbought Rejection: %B={pct_b:.2f} | RSI={self.rsi_val:.1f}',
                    confidence=0.83
                )

        return None
