"""Central Pivot Range (CPR) Price Action & Reversion Strategy."""
from datetime import time
from typing import Optional, Dict, Any
from nse_system.core.models import Candle, Signal
from nse_system.strategies.base import BaseStrategy
from nse_system.indicators.pivots import PivotEngine, CPRLevels

class CPRReversionStrategy(BaseStrategy):
    """Trades bounces off CPR levels on Wide CPR days and breakouts on Narrow CPR days."""

    def __init__(self, symbol: str, timeframe: str = '5m', params: Optional[Dict[str, Any]] = None):
        default_params = {
            'risk_reward': 2.0,
            'bounce_threshold_pct': 0.002
        }
        if params:
            default_params.update(params)
        super().__init__('CPR Price Action & Reversion', symbol, timeframe, default_params)
        self.cpr_levels: Optional[CPRLevels] = None
        self.current_date = None
        self.daily_high = 0.0
        self.daily_low = float('inf')
        self.daily_close = 0.0

    def on_candle(self, candle: Candle) -> Optional[Signal]:
        self.candles.append(candle)
        c_time = candle.timestamp.time()
        c_date = candle.timestamp.date()

        # Update daily tracking and calculate CPR for new day
        if c_date != self.current_date:
            if self.daily_high > 0 and self.daily_low < float('inf'):
                self.cpr_levels = PivotEngine.calculate_daily_cpr(
                    self.daily_high, self.daily_low, self.daily_close
                )
            else:
                # Approximate default CPR from candle
                self.cpr_levels = PivotEngine.calculate_daily_cpr(
                    candle.high * 1.008, candle.low * 0.992, candle.close
                )
            self.current_date = c_date
            self.daily_high = candle.high
            self.daily_low = candle.low
            self.daily_close = candle.close

        self.daily_high = max(self.daily_high, candle.high)
        self.daily_low = min(self.daily_low, candle.low)
        self.daily_close = candle.close

        if not self.cpr_levels:
            return None

        is_daily = 'd' in str(self.timeframe).lower()

        # 15:15 IST Square-off (Intraday only)
        if not is_daily and c_time >= time(15, 15):
            if self.current_position != 0:
                return self.exit_signal(candle, reason='15:15 Intraday Square-Off')
            return None

        # Position Exits
        if self.current_position > 0:
            if self.stop_loss and candle.low <= self.stop_loss:
                return self.exit_signal(candle, reason='CPR Long Stop Loss Hit')
            if self.target and candle.high >= self.target:
                return self.exit_signal(candle, reason='CPR Long Target Hit')

        elif self.current_position < 0:
            if self.stop_loss and candle.high >= self.stop_loss:
                return self.exit_signal(candle, reason='CPR Short Stop Loss Hit')
            if self.target and candle.low <= self.target:
                return self.exit_signal(candle, reason='CPR Short Target Hit')

        # Entry logic
        if self.current_position == 0 and (is_daily or (time(9, 30) <= c_time <= time(14, 0))):
            cpr = self.cpr_levels
            thresh = candle.close * self.params['bounce_threshold_pct']

            # Case A: Wide CPR -> Mean Reversion Bounce at Support (BC / S1)
            if cpr.cpr_type == 'WIDE':
                # Bounce at Bottom Central Support
                if abs(candle.low - cpr.bc) <= thresh and candle.close > cpr.bc:
                    sl = cpr.bc - (cpr.bc * 0.004)
                    tgt = cpr.tc
                    self.stop_loss = sl
                    self.target = tgt
                    return self.buy_signal(
                        candle, stop_loss=round(sl, 2), target=round(tgt, 2),
                        reason=f'Wide CPR: Bullish bounce at CPR BC support ({cpr.bc:.2f})',
                        confidence=0.82
                    )
                # Reversal at Top Central Resistance
                elif abs(candle.high - cpr.tc) <= thresh and candle.close < cpr.tc:
                    sl = cpr.tc + (cpr.tc * 0.004)
                    tgt = cpr.bc
                    self.stop_loss = sl
                    self.target = tgt
                    return self.sell_signal(
                        candle, stop_loss=round(sl, 2), target=round(tgt, 2),
                        reason=f'Wide CPR: Bearish rejection at CPR TC resistance ({cpr.tc:.2f})',
                        confidence=0.82
                    )

            # Case B: Narrow CPR -> Trending Breakout
            elif cpr.cpr_type == 'NARROW':
                if candle.close > cpr.tc and candle.open <= cpr.tc:
                    sl = cpr.bc
                    risk = candle.close - sl
                    tgt = candle.close + (risk * self.params['risk_reward'])
                    self.stop_loss = sl
                    self.target = tgt
                    return self.buy_signal(
                        candle, stop_loss=round(sl, 2), target=round(tgt, 2),
                        reason=f'Narrow CPR: Bullish breakout above TC ({cpr.tc:.2f})',
                        confidence=0.85
                    )
                elif candle.close < cpr.bc and candle.open >= cpr.bc:
                    sl = cpr.tc
                    risk = sl - candle.close
                    tgt = candle.close - (risk * self.params['risk_reward'])
                    self.stop_loss = sl
                    self.target = tgt
                    return self.sell_signal(
                        candle, stop_loss=round(sl, 2), target=round(tgt, 2),
                        reason=f'Narrow CPR: Bearish breakdown below BC ({cpr.bc:.2f})',
                        confidence=0.85
                    )

        return None
