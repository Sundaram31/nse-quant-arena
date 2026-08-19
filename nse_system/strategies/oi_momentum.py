"""Derivative Open Interest (OI) Long Buildup / Short Buildup Momentum Strategy."""
from datetime import time
from typing import Optional, Dict, Any
from nse_system.core.models import Candle, Signal
from nse_system.strategies.base import BaseStrategy

class OIMomentumStrategy(BaseStrategy):
    """Enters high-probability momentum trades when heavy Institutional Open Interest buildup confirms price breakout."""

    def __init__(self, symbol: str, timeframe: str = '5m', params: Optional[Dict[str, Any]] = None):
        default_params = {
            'oi_increase_threshold_pct': 0.03,
            'risk_reward': 2.0,
            'sl_pct': 0.007
        }
        if params:
            default_params.update(params)
        super().__init__('Options OI Buildup Breakout', symbol, timeframe, default_params)

    def on_candle(self, candle: Candle) -> Optional[Signal]:
        self.candles.append(candle)
        if len(self.candles) < 5:
            return None

        c_time = candle.timestamp.time()
        if c_time >= time(15, 15):
            if self.current_position != 0:
                return self.exit_signal(candle, reason='15:15 Intraday Square-Off')
            return None

        # Check Position Exits
        if self.current_position > 0:
            if self.stop_loss and candle.low <= self.stop_loss:
                return self.exit_signal(candle, reason='OI Long Stop Loss Hit')
            if self.target and candle.high >= self.target:
                return self.exit_signal(candle, reason='OI Long Target Hit')

        elif self.current_position < 0:
            if self.stop_loss and candle.high >= self.stop_loss:
                return self.exit_signal(candle, reason='OI Short Stop Loss Hit')
            if self.target and candle.low <= self.target:
                return self.exit_signal(candle, reason='OI Short Target Hit')

        # Entry logic based on OI change & Price Action
        prev_candle = self.candles[-2]
        oi_change = (candle.oi - prev_candle.oi) / max(1.0, prev_candle.oi)
        price_change = (candle.close - prev_candle.close) / max(1.0, prev_candle.close)

        if self.current_position == 0 and time(9, 30) <= c_time <= time(14, 0):
            # Institutional Long Buildup: Price UP > 0.3% with OI UP > 3%
            if price_change > 0.003 and oi_change > self.params['oi_increase_threshold_pct']:
                sl = candle.close * (1 - self.params['sl_pct'])
                risk = candle.close - sl
                tgt = candle.close + (risk * self.params['risk_reward'])
                self.stop_loss = sl
                self.target = tgt
                return self.buy_signal(
                    candle, stop_loss=round(sl, 2), target=round(tgt, 2),
                    reason=f'Institutional Long Buildup (Price +{price_change*100:.1f}%, OI +{oi_change*100:.1f}%)',
                    confidence=0.89
                )

            # Institutional Short Buildup: Price DOWN < -0.3% with OI UP > 3%
            elif price_change < -0.003 and oi_change > self.params['oi_increase_threshold_pct']:
                sl = candle.close * (1 + self.params['sl_pct'])
                risk = sl - candle.close
                tgt = candle.close - (risk * self.params['risk_reward'])
                self.stop_loss = sl
                self.target = tgt
                return self.sell_signal(
                    candle, stop_loss=round(sl, 2), target=round(tgt, 2),
                    reason=f'Institutional Short Buildup (Price {price_change*100:.1f}%, OI +{oi_change*100:.1f}%)',
                    confidence=0.89
                )

        return None
