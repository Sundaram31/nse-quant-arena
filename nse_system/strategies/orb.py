"""Opening Range Breakout (ORB 15m/30m) Strategy for NSE Equities & Indices."""
from datetime import time
from typing import Optional, Dict, Any
from nse_system.core.models import Candle, Signal
from nse_system.strategies.base import BaseStrategy

class ORBStrategy(BaseStrategy):
    """Trades breakouts above/below opening 15-minute or 30-minute range with Indian market timing rules."""

    def __init__(self, symbol: str, timeframe: str = '5m', params: Optional[Dict[str, Any]] = None):
        default_params = {
            'orb_minutes': 15,          # 15 or 30 minutes
            'risk_reward': 2.0,          # 1:2 R:R
            'max_loss_pct': 0.008,       # 0.8% stop loss cap
            'volume_filter_multiplier': 1.1
        }
        if params:
            default_params.update(params)
        super().__init__('Opening Range Breakout (ORB)', symbol, timeframe, default_params)
        
        self.orb_high: Optional[float] = None
        self.orb_low: Optional[float] = None
        self.orb_complete: bool = False
        self.current_date = None
        self.traded_today: bool = False

    def on_candle(self, candle: Candle) -> Optional[Signal]:
        self.candles.append(candle)
        c_time = candle.timestamp.time()
        c_date = candle.timestamp.date()

        # Reset daily state
        if c_date != self.current_date:
            self.current_date = c_date
            self.orb_high = None
            self.orb_low = None
            self.orb_complete = False
            self.traded_today = False

        is_daily = 'd' in str(self.timeframe).lower()

        if is_daily:
            if len(self.candles) < 5:
                return None
            prev_high = max(c.high for c in self.candles[-6:-1])
            prev_low = min(c.low for c in self.candles[-6:-1])
            self.orb_high = prev_high
            self.orb_low = prev_low
            self.orb_complete = True
        else:
            # Form Opening Range (09:15 to 09:30 for 15m ORB)
            orb_end_minute = 15 + self.params['orb_minutes']
            orb_end_hour = 9 + (orb_end_minute // 60)
            orb_end_min = orb_end_minute % 60
            orb_cutoff = time(orb_end_hour, orb_end_min)

            if c_time <= orb_cutoff:
                if self.orb_high is None or candle.high > self.orb_high:
                    self.orb_high = candle.high
                if self.orb_low is None or candle.low < self.orb_low:
                    self.orb_low = candle.low
                return None

            # Range is formed
            self.orb_complete = True

            # Intraday Square-off after 15:15 IST
            if c_time >= time(15, 15):
                if self.current_position != 0:
                    return self.exit_signal(candle, reason='Intraday 15:15 Auto Square-Off')
                return None

        # Check Position Exits (Target / Stop-Loss)
        if self.current_position > 0:
            if self.stop_loss and candle.low <= self.stop_loss:
                return self.exit_signal(candle, reason='ORB Long Stop-Loss Hit')
            if self.target and candle.high >= self.target:
                return self.exit_signal(candle, reason='ORB Long Target Hit')

        elif self.current_position < 0:
            if self.stop_loss and candle.high >= self.stop_loss:
                return self.exit_signal(candle, reason='ORB Short Stop-Loss Hit')
            if self.target and candle.low <= self.target:
                return self.exit_signal(candle, reason='ORB Short Target Hit')

        # Check for Breakout Entries
        if not self.traded_today and self.current_position == 0 and (is_daily or c_time < time(14, 0)):
            orb_range = self.orb_high - self.orb_low
            
            # Bullish Breakout above ORB High
            if candle.close > self.orb_high:
                sl = max(self.orb_high - orb_range * 0.5, candle.close * (1 - self.params['max_loss_pct']))
                risk = candle.close - sl
                tgt = candle.close + (risk * self.params['risk_reward'])
                self.stop_loss = sl
                self.target = tgt
                self.traded_today = True
                return self.buy_signal(
                    candle,
                    stop_loss=round(sl, 2),
                    target=round(tgt, 2),
                    reason=f'ORB Bullish Breakout above {self.orb_high:.2f}',
                    confidence=0.85
                )

            # Bearish Breakdown below ORB Low
            elif candle.close < self.orb_low:
                sl = min(self.orb_low + orb_range * 0.5, candle.close * (1 + self.params['max_loss_pct']))
                risk = sl - candle.close
                tgt = candle.close - (risk * self.params['risk_reward'])
                self.stop_loss = sl
                self.target = tgt
                self.traded_today = True
                return self.sell_signal(
                    candle,
                    stop_loss=round(sl, 2),
                    target=round(tgt, 2),
                    reason=f'ORB Bearish Breakdown below {self.orb_low:.2f}',
                    confidence=0.85
                )

        return None
