"""Comprehensive Risk Management System (RMS) & Circuit Breakers."""
from dataclasses import dataclass
from datetime import datetime, date
from typing import Dict, Tuple, Optional
from nse_system.core.models import Order, Portfolio, Position

@dataclass
class RMSConfig:
    max_daily_loss_pct: float = 0.03       # 3% max daily loss limit (Kill Switch)
    max_drawdown_pct: float = 0.08         # 8% max portfolio drawdown halt
    max_capital_per_trade_pct: float = 0.25 # 25% max allocation per symbol
    max_open_positions: int = 5            # Max simultaneous open positions
    kill_switch_active: bool = False

class RiskManager:
    """Risk Management System validating pre-trade checks and circuit breakers."""

    def __init__(self, config: Optional[RMSConfig] = None):
        self.config = config or RMSConfig()
        self.daily_start_capital: float = 0.0
        self.current_day: Optional[date] = None
        self.peak_capital: float = 0.0

    def reset_daily_session(self, current_capital: float, session_date: date):
        """Initialize RMS at the start of each trading session."""
        self.daily_start_capital = current_capital
        self.current_day = session_date
        self.peak_capital = max(self.peak_capital, current_capital)
        self.config.kill_switch_active = False

    def validate_order(
        self,
        order: Order,
        portfolio: Portfolio,
        current_price: float
    ) -> Tuple[bool, str]:
        """Pre-trade risk verification before sending order to broker/engine."""
        if self.config.kill_switch_active:
            return False, 'RMS REJECT: Kill Switch active due to risk limits.'

        total_val = portfolio.total_portfolio_value
        if self.daily_start_capital <= 0:
            self.daily_start_capital = total_val
        self.peak_capital = max(self.peak_capital, total_val)

        # 1. Daily Loss Limit Check (Kill Switch)
        daily_loss = self.daily_start_capital - total_val
        daily_loss_pct = (daily_loss / self.daily_start_capital) if self.daily_start_capital > 0 else 0
        if daily_loss_pct >= self.config.max_daily_loss_pct:
            self.config.kill_switch_active = True
            return False, f'RMS REJECT: Daily loss limit ({daily_loss_pct*100:.2f}% >= {self.config.max_daily_loss_pct*100:.1f}%) breached.'

        # 2. Max Drawdown Check
        drawdown_pct = (self.peak_capital - total_val) / max(1.0, self.peak_capital)
        if drawdown_pct >= self.config.max_drawdown_pct:
            self.config.kill_switch_active = True
            return False, f'RMS REJECT: Max portfolio drawdown ({drawdown_pct*100:.2f}% >= {self.config.max_drawdown_pct*100:.1f}%) breached.'

        # 3. Max Open Positions Check
        active_pos_count = sum(1 for p in portfolio.positions.values() if p.is_open)
        if active_pos_count >= self.config.max_open_positions:
            # Allow exits
            if order.symbol in portfolio.positions and portfolio.positions[order.symbol].is_open:
                pass
            else:
                return False, f'RMS REJECT: Max open positions ({self.config.max_open_positions}) reached.'

        # 4. Capital Allocation Limit
        order_val = order.quantity * current_price
        max_allowed_val = total_val * self.config.max_capital_per_trade_pct * 5.0 # With MIS leverage
        if order_val > max_allowed_val:
            return False, f'RMS REJECT: Order value ₹{order_val:.0f} exceeds max allowed per trade ₹{max_allowed_val:.0f}.'

        return True, 'APPROVED'
