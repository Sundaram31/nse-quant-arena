"""Event-Driven Backtest Engine with Real NSE Indian Taxes & Slippage."""
from datetime import datetime, time
from typing import List, Dict, Any, Optional
import pandas as pd

from nse_system.core.constants import OrderSide, OrderType, ProductType, MarketHours
from nse_system.core.models import Candle, Order, Position, Trade, Portfolio, StrategyPerformance
from nse_system.core.tax_calculator import NSETaxCalculator
from nse_system.strategies.base import BaseStrategy
from nse_system.risk.rms import RiskManager, RMSConfig
from nse_system.risk.position_sizer import PositionSizer
from nse_system.engine.metrics import QuantMetricsCalculator

class BacktestEngine:
    """Simulates strategy execution with realistic market fills, slippage, and Indian regulatory taxes."""

    def __init__(
        self,
        strategy: BaseStrategy,
        initial_capital: float = 100000.0,
        slippage_pct: float = 0.0005,  # 0.05% slippage
        rms_config: Optional[RMSConfig] = None
    ):
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.slippage_pct = slippage_pct
        self.rms = RiskManager(rms_config)
        self.portfolio = Portfolio(initial_capital=initial_capital, cash=initial_capital)
        self.trades: List[Trade] = []
        self.equity_history: List[Dict[str, Any]] = []

    def run(self, candles: List[Candle]) -> StrategyPerformance:
        """Run backtest across historical candles."""
        self.strategy.on_start()
        self.trades = []
        self.portfolio = Portfolio(initial_capital=self.initial_capital, cash=self.initial_capital)
        self.equity_history = []

        current_entry_price = 0.0
        current_entry_time = None
        current_qty = 0
        current_side = None
        current_order_id = ''
        last_date = None

        for candle in candles:
            c_date = candle.timestamp.date()
            c_time = candle.timestamp.time()

            # Session initialization for RMS
            if c_date != last_date:
                self.rms.reset_daily_session(self.portfolio.total_portfolio_value, c_date)
                last_date = c_date

            # Strategy signal generation
            signal = self.strategy.on_candle(candle)

            if signal:
                # 1. Handle Exit Signal
                if signal.signal_type in ('EXIT_LONG', 'EXIT_SHORT') and current_qty != 0:
                    exit_slippage = -self.slippage_pct if current_side == OrderSide.BUY else self.slippage_pct
                    exit_price = candle.close * (1 + exit_slippage)
                    exit_time = candle.timestamp

                    if current_side == OrderSide.BUY:
                        gross_pnl = (exit_price - current_entry_price) * current_qty
                        buy_p, sell_p = current_entry_price, exit_price
                    else:
                        gross_pnl = (current_entry_price - exit_price) * current_qty
                        buy_p, sell_p = exit_price, current_entry_price

                    # Calculate Indian Taxes (STT, GST, Exchange, SEBI, Stamp)
                    costs = NSETaxCalculator.calculate_trade_costs(
                        buy_price=buy_p,
                        sell_price=sell_p,
                        quantity=current_qty,
                        product_type=self.strategy.product_type
                    )
                    net_pnl = gross_pnl - costs.total_charges
                    ret_pct = (gross_pnl / (current_entry_price * current_qty)) * 100.0 if current_entry_price > 0 else 0.0
                    duration = (exit_time - current_entry_time).total_seconds() / 60.0

                    trade = Trade(
                        trade_id=f'TR_{len(self.trades)+1}',
                        order_id=current_order_id,
                        symbol=self.strategy.symbol,
                        side=current_side,
                        product_type=self.strategy.product_type,
                        quantity=current_qty,
                        entry_price=round(current_entry_price, 2),
                        exit_price=round(exit_price, 2),
                        entry_time=current_entry_time,
                        exit_time=exit_time,
                        gross_pnl=round(gross_pnl, 2),
                        net_pnl=round(net_pnl, 2),
                        taxes=round(costs.total_charges, 2),
                        return_pct=round(ret_pct, 2),
                        holding_duration_mins=round(duration, 1),
                        exit_reason=signal.reason
                    )
                    self.trades.append(trade)
                    self.portfolio.cash += net_pnl
                    
                    # Update strategy state
                    exit_order = Order(
                        order_id=f'EX_{len(self.trades)}',
                        symbol=self.strategy.symbol,
                        side=OrderSide.SELL if current_side == OrderSide.BUY else OrderSide.BUY,
                        order_type=OrderType.MARKET,
                        quantity=current_qty,
                        avg_price=exit_price
                    )
                    self.strategy.on_order_update(exit_order)
                    current_qty = 0
                    current_side = None

                # 2. Handle Entry Signal
                elif signal.signal_type in ('BUY', 'SELL') and current_qty == 0:
                    entry_side = OrderSide.BUY if signal.signal_type == 'BUY' else OrderSide.SELL
                    entry_slippage = self.slippage_pct if entry_side == OrderSide.BUY else -self.slippage_pct
                    fill_price = signal.price * (1 + entry_slippage)

                    qty = PositionSizer.calculate_quantity(
                        capital=self.portfolio.total_portfolio_value,
                        price=fill_price,
                        stop_loss=signal.stop_loss,
                        symbol=self.strategy.symbol,
                        risk_per_trade_pct=0.01
                    )

                    new_order = Order(
                        order_id=f'ORD_{len(self.trades)+1}',
                        symbol=self.strategy.symbol,
                        side=entry_side,
                        order_type=OrderType.MARKET,
                        product_type=self.strategy.product_type,
                        quantity=qty,
                        price=fill_price,
                        avg_price=fill_price,
                        filled_quantity=qty
                    )

                    # RMS validation
                    approved, reason = self.rms.validate_order(new_order, self.portfolio, fill_price)
                    if approved:
                        current_entry_price = fill_price
                        current_entry_time = candle.timestamp
                        current_qty = qty
                        current_side = entry_side
                        current_order_id = new_order.order_id
                        self.strategy.on_order_update(new_order)

            # Record equity snapshot
            unrealized = 0.0
            if current_qty > 0:
                if current_side == OrderSide.BUY:
                    unrealized = (candle.close - current_entry_price) * current_qty
                else:
                    unrealized = (current_entry_price - candle.close) * current_qty

            self.equity_history.append({
                'timestamp': candle.timestamp,
                'equity': round(self.portfolio.cash + unrealized, 2),
                'close': candle.close
            })

        self.strategy.on_stop()

        # Calculate final quant metrics
        perf = QuantMetricsCalculator.calculate_performance(
            strategy_name=self.strategy.name,
            symbol=self.strategy.symbol,
            trades=self.trades,
            initial_capital=self.initial_capital,
            equity_curve=self.equity_history
        )
        return perf
