"""Real-Time Paper Trading Execution Engine."""
from datetime import datetime, time
from typing import Dict, List, Optional, Callable
import threading

from nse_system.core.constants import OrderSide, OrderType, ProductType, MarketHours
from nse_system.core.models import Candle, Tick, Order, Position, Trade, Portfolio
from nse_system.core.tax_calculator import NSETaxCalculator
from nse_system.strategies.base import BaseStrategy
from nse_system.risk.rms import RiskManager, RMSConfig
from nse_system.risk.position_sizer import PositionSizer
from nse_system.risk.auto_squareoff import IntradayAutoSquareoff

class PaperTradingEngine:
    """Real-time execution engine managing live paper positions, simulated fills, and risk supervisors."""

    def __init__(
        self,
        strategy: BaseStrategy,
        initial_capital: float = 100000.0,
        rms_config: Optional[RMSConfig] = None
    ):
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.portfolio = Portfolio(initial_capital=initial_capital, cash=initial_capital)
        self.rms = RiskManager(rms_config)
        self.orders: List[Order] = []
        self.trades: List[Trade] = []
        self.is_running: bool = False
        self._lock = threading.Lock()
        self.on_trade_callbacks: List[Callable[[Trade], None]] = []

    def start(self):
        """Starts the paper trading engine session."""
        with self._lock:
            self.is_running = True
            self.strategy.on_start()
            self.rms.reset_daily_session(self.portfolio.total_portfolio_value, datetime.now().date())

    def stop(self):
        """Stops the paper trading engine."""
        with self._lock:
            self.is_running = False
            self.strategy.on_stop()

    def on_candle(self, candle: Candle):
        """Processes an incoming candle."""
        if not self.is_running:
            return

        with self._lock:
            c_time = candle.timestamp.time()

            # 1. 15:15 IST Mandatory Intraday Auto-Squareoff Check
            if IntradayAutoSquareoff.is_squareoff_time(c_time):
                open_positions = [p for p in self.portfolio.positions.values() if p.is_open]
                for pos in open_positions:
                    self._close_position(pos.symbol, candle.close, candle.timestamp, '15:15 Auto Square-Off')
                return

            # 2. Update existing position LTP & unrealized PnL
            if self.strategy.symbol in self.portfolio.positions:
                self.portfolio.positions[self.strategy.symbol].ltp = candle.close

            # 3. Process strategy candle
            signal = self.strategy.on_candle(candle)

            if signal:
                cur_pos = self.portfolio.positions.get(self.strategy.symbol)
                has_open_pos = cur_pos is not None and cur_pos.is_open

                # Handle Exit Signal
                if signal.signal_type in ('EXIT_LONG', 'EXIT_SHORT') and has_open_pos:
                    self._close_position(self.strategy.symbol, candle.close, candle.timestamp, signal.reason)

                # Handle Entry Signal
                elif signal.signal_type in ('BUY', 'SELL') and not has_open_pos:
                    self._open_position(signal, candle)

    def _open_position(self, signal, candle: Candle):
        side = OrderSide.BUY if signal.signal_type == 'BUY' else OrderSide.SELL
        fill_price = candle.close

        qty = PositionSizer.calculate_quantity(
            capital=self.portfolio.total_portfolio_value,
            price=fill_price,
            stop_loss=signal.stop_loss,
            symbol=self.strategy.symbol,
            risk_per_trade_pct=0.01
        )

        order = Order(
            order_id=f'PAP_ORD_{len(self.orders)+1}',
            symbol=self.strategy.symbol,
            side=side,
            order_type=OrderType.MARKET,
            product_type=self.strategy.product_type,
            quantity=qty,
            price=fill_price,
            avg_price=fill_price,
            filled_quantity=qty
        )

        approved, reason = self.rms.validate_order(order, self.portfolio, fill_price)
        if not approved:
            order.reject_reason = reason
            self.orders.append(order)
            return

        self.orders.append(order)

        # Update position
        pos_qty = qty if side == OrderSide.BUY else -qty
        self.portfolio.positions[self.strategy.symbol] = Position(
            symbol=self.strategy.symbol,
            product_type=self.strategy.product_type,
            quantity=pos_qty,
            avg_price=fill_price,
            ltp=fill_price
        )
        self.strategy.on_order_update(order)

    def _close_position(self, symbol: str, exit_price: float, exit_time: datetime, reason: str):
        pos = self.portfolio.positions.get(symbol)
        if not pos or not pos.is_open:
            return

        qty = abs(pos.quantity)
        is_long = pos.quantity > 0
        side = OrderSide.BUY if is_long else OrderSide.SELL
        entry_price = pos.avg_price

        if is_long:
            gross_pnl = (exit_price - entry_price) * qty
            buy_p, sell_p = entry_price, exit_price
        else:
            gross_pnl = (entry_price - exit_price) * qty
            buy_p, sell_p = exit_price, entry_price

        costs = NSETaxCalculator.calculate_trade_costs(
            buy_price=buy_p,
            sell_price=sell_p,
            quantity=qty,
            product_type=pos.product_type
        )
        net_pnl = gross_pnl - costs.total_charges
        ret_pct = (gross_pnl / (entry_price * qty)) * 100.0 if entry_price > 0 else 0.0

        trade = Trade(
            trade_id=f'PAP_TR_{len(self.trades)+1}',
            order_id=f'PAP_EX_{len(self.orders)+1}',
            symbol=symbol,
            side=side,
            product_type=pos.product_type,
            quantity=qty,
            entry_price=round(entry_price, 2),
            exit_price=round(exit_price, 2),
            entry_time=exit_time,
            exit_time=exit_time,
            gross_pnl=round(gross_pnl, 2),
            net_pnl=round(net_pnl, 2),
            taxes=round(costs.total_charges, 2),
            return_pct=round(ret_pct, 2),
            holding_duration_mins=15.0,
            exit_reason=reason
        )
        self.trades.append(trade)
        self.portfolio.closed_trades.append(trade)
        self.portfolio.cash += net_pnl

        # Reset position
        pos.quantity = 0
        pos.avg_price = 0.0
        pos.realized_pnl += net_pnl

        exit_order = Order(
            order_id=trade.order_id,
            symbol=symbol,
            side=OrderSide.SELL if is_long else OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=qty,
            avg_price=exit_price
        )
        self.orders.append(exit_order)
        self.strategy.on_order_update(exit_order)

        for cb in self.on_trade_callbacks:
            try:
                cb(trade)
            except Exception:
                pass
