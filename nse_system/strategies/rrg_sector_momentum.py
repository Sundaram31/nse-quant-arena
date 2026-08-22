"""RRG Sector Rotation & Leadership Momentum Strategy (Optimized)."""
from datetime import time
from typing import Optional, Dict, Any
from nse_system.core.models import Candle, Signal
from nse_system.strategies.base import BaseStrategy

class RRGSectorMomentumStrategy(BaseStrategy):
    """Focuses on riding leaders in the Leading & Improving quadrants of the RRG chart."""

    def __init__(self, symbol: str, timeframe: str = '5m', params: Optional[Dict[str, Any]] = None):
        default_params = {
            'is_leading_sector': True,
            'risk_reward': 2.2,
            'sl_pct': 0.008
        }
        if params:
            default_params.update(params)
        super().__init__('RRG Sector Rotation Momentum', symbol, timeframe, default_params)
        self.fast_ema = 0.0
        self.slow_ema = 0.0
        self.avg_gain = 0.0
        self.avg_loss = 0.0
        self.rsi_val = 50.0

    def on_start(self):
        super().on_start()
        self.fast_ema = 0.0
        self.slow_ema = 0.0
        self.avg_gain = 0.0
        self.avg_loss = 0.0
        self.rsi_val = 50.0

    def on_candle(self, candle: Candle) -> Optional[Signal]:
        self.candles.append(candle)
        cur_close = candle.close
        c_time = candle.timestamp.time()

        if len(self.candles) == 1:
            self.fast_ema = cur_close
            self.slow_ema = cur_close
            return None

        # Incremental EMA 9 & 21
        a9 = 2.0 / 10.0
        a21 = 2.0 / 22.0
        self.fast_ema = a9 * cur_close + (1 - a9) * self.fast_ema
        self.slow_ema = a21 * cur_close + (1 - a21) * self.slow_ema

        # Incremental RSI
        prev_close = self.candles[-2].close
        diff = cur_close - prev_close
        gain = max(0.0, diff)
        loss = max(0.0, -diff)
        a_rsi = 1.0 / 14.0
        self.avg_gain = a_rsi * gain + (1 - a_rsi) * self.avg_gain
        self.avg_loss = a_rsi * loss + (1 - a_rsi) * self.avg_loss
        rs = self.avg_gain / max(1e-6, self.avg_loss)
        self.rsi_val = 100.0 - (100.0 / (1.0 + rs))

        if len(self.candles) < 21:
            return None

        is_daily = 'd' in str(self.timeframe).lower()

        if not is_daily and c_time >= time(15, 15):
            if self.current_position != 0:
                return self.exit_signal(candle, reason='15:15 Intraday Square-Off')
            return None

        # Position Exits
        if self.current_position > 0:
            if self.stop_loss and candle.low <= self.stop_loss:
                return self.exit_signal(candle, reason='RRG Long Stop Loss Hit')
            if self.target and candle.high >= self.target:
                return self.exit_signal(candle, reason='RRG Long Target Hit')

        elif self.current_position < 0:
            if self.stop_loss and candle.high >= self.stop_loss:
                return self.exit_signal(candle, reason='RRG Short Stop Loss Hit')
            if self.target and candle.low <= self.target:
                return self.exit_signal(candle, reason='RRG Short Target Hit')

        if self.current_position == 0 and (is_daily or (time(9, 30) <= c_time <= time(14, 0))):
            if self.params.get('is_leading_sector', True):
                if self.fast_ema > self.slow_ema and self.rsi_val > 55:
                    sl = candle.close * (1 - self.params['sl_pct'])
                    risk = candle.close - sl
                    tgt = candle.close + (risk * self.params['risk_reward'])
                    self.stop_loss = sl
                    self.target = tgt
                    return self.buy_signal(
                        candle, stop_loss=round(sl, 2), target=round(tgt, 2),
                        reason=f'RRG Leading Sector Outperformer Momentum | RSI={self.rsi_val:.1f}',
                        confidence=0.90
                    )
            else:
                if self.fast_ema < self.slow_ema and self.rsi_val < 45:
                    sl = candle.close * (1 + self.params['sl_pct'])
                    risk = sl - candle.close
                    tgt = candle.close - (risk * self.params['risk_reward'])
                    self.stop_loss = sl
                    self.target = tgt
                    return self.sell_signal(
                        candle, stop_loss=round(sl, 2), target=round(tgt, 2),
                        reason=f'RRG Lagging Sector Laggard Short Momentum | RSI={self.rsi_val:.1f}',
                        confidence=0.90
                    )

        return None
