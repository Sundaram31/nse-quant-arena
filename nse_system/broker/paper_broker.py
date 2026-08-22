"""Simulated Paper Broker with live margins, position tracking, trailing SL, and tax-aware PnL."""
from typing import Dict, List, Optional, Any
from datetime import datetime
from nse_system.broker.base import BaseBroker
from nse_system.core.constants import OrderSide, OrderType, OrderStatus, ProductType
from nse_system.core.models import Order, Position, Trade
from nse_system.core.tax_calculator import NSETaxCalculator

class PaperBroker(BaseBroker):
    """In-memory paper trading broker with full position, trailing SL, and PnL management."""

    def __init__(self, initial_capital: float = 100000.0):
        self.capital = initial_capital
        self.cash = initial_capital
        self.used_margin = 0.0
        self.orders: Dict[str, Order] = {}
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.stop_losses: Dict[str, float] = {}
        self.targets: Dict[str, float] = {}
        self.trailing_sl_anchors: Dict[str, float] = {}
        self._connected = False

    def connect(self) -> bool:
        self._connected = True
        return True

    def get_margins(self) -> Dict[str, float]:
        unrealized = sum(pos.unrealized_pnl for pos in self.positions.values() if pos.is_open)
        return {
            'available_cash': self.cash - self.used_margin,
            'used_margin': self.used_margin,
            'total_collateral': self.capital,
            'net_equity': self.cash + unrealized
        }

    def place_order(self, order: Order) -> Order:
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        if order.avg_price <= 0.0:
            order.avg_price = order.price
        order.updated_at = datetime.now()
        self.orders[order.order_id] = order

        sym = order.symbol
        side = order.side
        qty = order.quantity
        price = order.avg_price

        # Update position tracking
        if sym not in self.positions:
            self.positions[sym] = Position(
                symbol=sym,
                product_type=order.product_type,
                quantity=0,
                avg_price=0.0,
                ltp=price
            )

        pos = self.positions[sym]
        pos.ltp = price

        if side == OrderSide.BUY:
            if pos.quantity < 0:
                # Closing short position (partial or full)
                close_qty = min(qty, abs(pos.quantity))
                gross_pnl = (pos.avg_price - price) * close_qty
                costs = NSETaxCalculator.calculate_trade_costs(
                    buy_price=price,
                    sell_price=pos.avg_price,
                    quantity=close_qty,
                    product_type=pos.product_type
                )
                net_pnl = gross_pnl - costs.total_charges
                pos.realized_pnl += net_pnl
                self.cash += net_pnl
                
                trade = Trade(
                    trade_id=f'TR_{len(self.trades)+1}',
                    order_id=order.order_id,
                    symbol=sym,
                    side=OrderSide.SELL,
                    product_type=pos.product_type,
                    quantity=close_qty,
                    entry_price=pos.avg_price,
                    exit_price=price,
                    entry_time=order.created_at,
                    exit_time=datetime.now(),
                    gross_pnl=round(gross_pnl, 2),
                    net_pnl=round(net_pnl, 2),
                    taxes=round(costs.total_charges, 2),
                    return_pct=round((gross_pnl / (pos.avg_price * close_qty)) * 100.0 if pos.avg_price > 0 else 0.0, 2),
                    holding_duration_mins=15.0,
                    exit_reason='COVER_SHORT'
                )
                self.trades.append(trade)
                
                rem_short = pos.quantity + close_qty  # negative + positive
                rem_buy = qty - close_qty
                if rem_short < 0:
                    pos.quantity = rem_short
                else:
                    pos.quantity = rem_buy
                    pos.avg_price = price
            else:
                # Adding to long
                total_val = (pos.avg_price * pos.quantity) + (price * qty)
                pos.quantity += qty
                pos.avg_price = total_val / pos.quantity if pos.quantity > 0 else price
        else: # SELL
            if pos.quantity > 0:
                # Closing long position (partial or full)
                close_qty = min(qty, pos.quantity)
                gross_pnl = (price - pos.avg_price) * close_qty
                costs = NSETaxCalculator.calculate_trade_costs(
                    buy_price=pos.avg_price,
                    sell_price=price,
                    quantity=close_qty,
                    product_type=pos.product_type
                )
                net_pnl = gross_pnl - costs.total_charges
                pos.realized_pnl += net_pnl
                self.cash += net_pnl

                trade = Trade(
                    trade_id=f'TR_{len(self.trades)+1}',
                    order_id=order.order_id,
                    symbol=sym,
                    side=OrderSide.BUY,
                    product_type=pos.product_type,
                    quantity=close_qty,
                    entry_price=pos.avg_price,
                    exit_price=price,
                    entry_time=order.created_at,
                    exit_time=datetime.now(),
                    gross_pnl=round(gross_pnl, 2),
                    net_pnl=round(net_pnl, 2),
                    taxes=round(costs.total_charges, 2),
                    return_pct=round((gross_pnl / (pos.avg_price * close_qty)) * 100.0 if pos.avg_price > 0 else 0.0, 2),
                    holding_duration_mins=15.0,
                    exit_reason='SELL_LONG'
                )
                self.trades.append(trade)

                rem_long = pos.quantity - close_qty
                rem_sell = qty - close_qty
                if rem_long > 0:
                    pos.quantity = rem_long
                else:
                    pos.quantity = -rem_sell
                    pos.avg_price = price if rem_sell > 0 else 0.0
            else:
                # Adding to short
                total_val = (pos.avg_price * abs(pos.quantity)) + (price * qty)
                pos.quantity -= qty
                pos.avg_price = total_val / abs(pos.quantity) if pos.quantity != 0 else price

        self._recalculate_used_margin()
        return order

    def _recalculate_used_margin(self):
        self.used_margin = sum(abs(p.quantity) * p.avg_price * 0.20 for p in self.positions.values() if p.is_open)

    def buy(
        self,
        symbol: str,
        quantity: int,
        price: float,
        stop_loss: Optional[float] = None,
        target: Optional[float] = None,
        product_type: ProductType = ProductType.MIS,
        tag: str = ''
    ) -> Order:
        """Convenience method to place a BUY order."""
        order = Order(
            order_id=f'PAP_ORD_{len(self.orders)+1}',
            symbol=symbol,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            product_type=product_type,
            quantity=quantity,
            price=price,
            avg_price=price,
            tag=tag
        )
        if stop_loss is not None:
            self.stop_losses[symbol] = stop_loss
            self.trailing_sl_anchors[symbol] = price
        if target is not None:
            self.targets[symbol] = target
        return self.place_order(order)

    def sell(
        self,
        symbol: str,
        quantity: int,
        price: float,
        stop_loss: Optional[float] = None,
        target: Optional[float] = None,
        product_type: ProductType = ProductType.MIS,
        tag: str = ''
    ) -> Order:
        """Convenience method to place a SELL order."""
        order = Order(
            order_id=f'PAP_ORD_{len(self.orders)+1}',
            symbol=symbol,
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            product_type=product_type,
            quantity=quantity,
            price=price,
            avg_price=price,
            tag=tag
        )
        if stop_loss is not None:
            self.stop_losses[symbol] = stop_loss
            self.trailing_sl_anchors[symbol] = price
        if target is not None:
            self.targets[symbol] = target
        return self.place_order(order)

    def close_position(self, symbol: str, exit_price: Optional[float] = None) -> Optional[Trade]:
        """Closes any open position for the symbol."""
        pos = self.positions.get(symbol)
        if not pos or not pos.is_open:
            return None

        p_close = exit_price if exit_price is not None else pos.ltp
        side = OrderSide.SELL if pos.quantity > 0 else OrderSide.BUY
        qty = abs(pos.quantity)

        order = Order(
            order_id=f'PAP_CLS_{len(self.orders)+1}',
            symbol=symbol,
            side=side,
            order_type=OrderType.MARKET,
            product_type=pos.product_type,
            quantity=qty,
            price=p_close,
            avg_price=p_close,
            tag='CLOSE'
        )
        self.place_order(order)
        self.stop_losses.pop(symbol, None)
        self.targets.pop(symbol, None)
        self.trailing_sl_anchors.pop(symbol, None)
        return self.trades[-1] if self.trades else None

    def close_all_positions(self, exit_prices: Optional[Dict[str, float]] = None) -> List[Trade]:
        """Closes all currently open positions."""
        closed = []
        open_syms = [sym for sym, pos in self.positions.items() if pos.is_open]
        for sym in open_syms:
            px = exit_prices.get(sym) if exit_prices else None
            tr = self.close_position(sym, px)
            if tr:
                closed.append(tr)
        return closed

    def update_trailing_sl(
        self,
        symbol: str,
        current_price: float,
        trail_amount: Optional[float] = None,
        trailing_pct: Optional[float] = None
    ) -> Optional[float]:
        """Updates dynamic trailing stop-loss for an open position."""
        pos = self.positions.get(symbol)
        if not pos or not pos.is_open:
            return None

        pos.ltp = current_price
        current_sl = self.stop_losses.get(symbol)
        is_long = pos.quantity > 0

        if is_long:
            if trail_amount is not None:
                new_sl = current_price - trail_amount
            elif trailing_pct is not None:
                new_sl = current_price * (1.0 - (trailing_pct / 100.0))
            else:
                return current_sl

            if current_sl is None or new_sl > current_sl:
                self.stop_losses[symbol] = round(new_sl, 2)
                return self.stop_losses[symbol]
        else: # short
            if trail_amount is not None:
                new_sl = current_price + trail_amount
            elif trailing_pct is not None:
                new_sl = current_price * (1.0 + (trailing_pct / 100.0))
            else:
                return current_sl

            if current_sl is None or new_sl < current_sl:
                self.stop_losses[symbol] = round(new_sl, 2)
                return self.stop_losses[symbol]

        return self.stop_losses.get(symbol)

    def calculate_pnl(
        self,
        symbol: Optional[str] = None,
        current_prices: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """Calculates realized, unrealized, and net PnL across active and closed trades."""
        if current_prices:
            for s, px in current_prices.items():
                if s in self.positions:
                    self.positions[s].ltp = px

        if symbol:
            pos = self.positions.get(symbol)
            if not pos:
                return {'symbol': symbol, 'realized_pnl': 0.0, 'unrealized_pnl': 0.0, 'net_pnl': 0.0}
            return {
                'symbol': symbol,
                'quantity': pos.quantity,
                'avg_price': pos.avg_price,
                'ltp': pos.ltp,
                'realized_pnl': round(pos.realized_pnl, 2),
                'unrealized_pnl': round(pos.unrealized_pnl, 2),
                'net_pnl': round(pos.realized_pnl + pos.unrealized_pnl, 2)
            }

        total_realized = sum(t.net_pnl for t in self.trades)
        total_unrealized = sum(p.unrealized_pnl for p in self.positions.values() if p.is_open)
        total_gross = sum(t.gross_pnl for t in self.trades)
        total_taxes = sum(t.taxes for t in self.trades)

        return {
            'total_realized_pnl': round(total_realized, 2),
            'total_unrealized_pnl': round(total_unrealized, 2),
            'total_net_pnl': round(total_realized + total_unrealized, 2),
            'total_gross_pnl': round(total_gross, 2),
            'total_taxes': round(total_taxes, 2),
            'total_trades': len(self.trades),
            'open_positions_count': sum(1 for p in self.positions.values() if p.is_open)
        }

    def cancel_order(self, order_id: str) -> bool:
        if order_id in self.orders:
            self.orders[order_id].status = OrderStatus.CANCELLED
            return True
        return False

    def get_positions(self) -> List[Position]:
        return list(self.positions.values())

    def get_open_positions(self) -> List[Position]:
        return [p for p in self.positions.values() if p.is_open]

    def get_orders(self) -> List[Order]:
        return list(self.orders.values())

    def get_trades(self) -> List[Trade]:
        return list(self.trades)

